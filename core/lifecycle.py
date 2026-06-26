"""Account lifecycle management — periodic checks, auto-renewal, expiry warnings."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from core.account_graph import load_account_graphs, patch_account_graph
from core.base_platform import AccountStatus, RegisterConfig
from core.db import AccountModel, AccountOverviewModel, engine
from core.datetime_utils import _utcnow, _utcnow_iso, _utcnow_ts
from core.platform_accounts import build_platform_account
from core.registry import get

logger = logging.getLogger(__name__)

# Initial delay before first lifecycle check (seconds)
LIFECYCLE_STARTUP_DELAY = 30


# ---------------------------------------------------------------------------
# Account validity check
# ---------------------------------------------------------------------------

def check_accounts_validity(
    *,
    platform: str = "",
    limit: int = 100,
    log_fn=None,
) -> dict[str, int]:
    """Check validity of active accounts. Returns {valid, invalid, error, skipped}."""
    log = log_fn or logger.info

    with Session(engine) as session:
        q = select(AccountModel)
        if platform:
            q = q.where(AccountModel.platform == platform)
        q = q.order_by(AccountModel.created_at.desc(), AccountModel.id.desc())
        accounts = session.exec(q.limit(limit)).all()
        graphs = load_account_graphs(session, [int(a.id) for a in accounts if a.id])

    # Only check accounts that are in an active lifecycle state
    active_statuses = {"registered", "trial", "subscribed"}
    targets = [
        a for a in accounts
        if graphs.get(int(a.id or 0), {}).get("lifecycle_status") in active_statuses
    ]

    results = {"valid": 0, "invalid": 0, "error": 0, "skipped": len(accounts) - len(targets)}
    for acc in targets:
        try:
            platform_cls = get(acc.platform)
            plugin = platform_cls(config=RegisterConfig())
            with Session(engine) as session:
                current = session.get(AccountModel, acc.id)
                if not current:
                    continue
                account_obj = build_platform_account(session, current)

            valid = plugin.check_valid(account_obj)
            with Session(engine) as session:
                model = session.get(AccountModel, acc.id)
                if model:
                    model.updated_at = _utcnow()
                    summary_updates = {"checked_at": _utcnow_iso(), "valid": valid}
                    if hasattr(plugin, "get_last_check_overview"):
                        summary_updates.update(plugin.get_last_check_overview() or {})
                    patch_account_graph(
                        session, model,
                        summary_updates=summary_updates,
                    )
                    session.add(model)
                    session.commit()
            if valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
                log(f"  {acc.email} ({acc.platform}): invalid")
        except Exception as exc:
            results["error"] += 1
            log(f"  {acc.email} ({acc.platform}): check error {exc}")

    log(f"Check complete: valid {results['valid']}, invalid {results['invalid']}, "
        f"error {results['error']}, skipped {results['skipped']}")
    return results


# ---------------------------------------------------------------------------
# Token auto-refresh (ChatGPT-specific for now, extensible)
# ---------------------------------------------------------------------------

def refresh_expiring_tokens(
    *,
    platform: str = "",
    hours_before_expiry: int = 24,
    limit: int = 50,
    log_fn=None,
) -> dict[str, int]:
    """Refresh tokens that are about to expire within `hours_before_expiry` hours."""
    log = log_fn or logger.info
    results = {"refreshed": 0, "failed": 0, "skipped": 0}

    with Session(engine) as session:
        q = select(AccountModel)
        if platform:
            q = q.where(AccountModel.platform == platform)
        accounts = session.exec(q.limit(limit)).all()
        graphs = load_account_graphs(session, [int(a.id) for a in accounts if a.id])

    active_statuses = {"registered", "trial", "subscribed"}
    for acc in accounts:
        graph = graphs.get(int(acc.id or 0), {})
        if graph.get("lifecycle_status") not in active_statuses:
            results["skipped"] += 1
            continue

        # Currently only ChatGPT has token refresh support
        if acc.platform != "chatgpt":
            results["skipped"] += 1
            continue

        credentials = {
            c["key"]: c["value"]
            for c in (graph.get("credentials") or [])
            if c.get("scope") == "platform"
        }
        refresh_token = credentials.get("refresh_token", "")
        session_token = credentials.get("session_token", "")
        if not refresh_token and not session_token:
            results["skipped"] += 1
            continue

        try:
            from platforms.chatgpt.token_refresh import TokenRefreshManager

            class _Account:
                pass

            a = _Account()
            a.email = acc.email
            a.session_token = session_token
            a.refresh_token = refresh_token
            a.client_id = credentials.get("client_id", "")

            proxy = None  # Could be enhanced to use proxy pool
            manager = TokenRefreshManager(proxy_url=proxy)
            result = manager.refresh_account(a)

            if result.success:
                credential_updates = {}
                if result.access_token:
                    credential_updates["access_token"] = result.access_token
                if result.refresh_token:
                    credential_updates["refresh_token"] = result.refresh_token

                with Session(engine) as session:
                    model = session.get(AccountModel, acc.id)
                    if model and credential_updates:
                        model.updated_at = _utcnow()
                        patch_account_graph(
                            session, model,
                            credential_updates=credential_updates,
                            summary_updates={
                                "last_refresh_at": _utcnow_iso(),
                                "refresh_success": True,
                            },
                        )
                        session.add(model)
                        session.commit()
                results["refreshed"] += 1
                log(f"  ✓ {acc.email}: token refresh succeeded")
            else:
                results["failed"] += 1
                log(f"  ✗ {acc.email}: {result.error_message}")
        except Exception as exc:
            results["failed"] += 1
            log(f"  ✗ {acc.email}: refresh error {exc}")

    log(f"Refresh complete: success {results['refreshed']}, failed {results['failed']}, "
        f"skipped {results['skipped']}")
    return results


# ---------------------------------------------------------------------------
# Trial expiry warning
# ---------------------------------------------------------------------------

def flag_expiring_trials(
    *,
    hours_warning: int = 48,
    log_fn=None,
) -> dict[str, int]:
    """Flag trial accounts that will expire within `hours_warning` hours."""
    log = log_fn or logger.info
    now_ts = _utcnow_ts()
    warning_ts = now_ts + hours_warning * 3600
    results = {"warned": 0, "expired": 0, "skipped": 0}

    with Session(engine) as session:
        overviews = session.exec(
            select(AccountOverviewModel)
            .where(AccountOverviewModel.lifecycle_status == "trial")
        ).all()

    for overview in overviews:
        summary = overview.get_summary()
        trial_end = int(summary.get("trial_end_time") or 0)
        if not trial_end:
            results["skipped"] += 1
            continue

        if trial_end < now_ts:
            # Already expired
            with Session(engine) as session:
                model = session.get(AccountModel, overview.account_id)
                if model:
                    model.updated_at = _utcnow()
                    patch_account_graph(
                        session, model,
                        lifecycle_status=AccountStatus.EXPIRED.value,
                        summary_updates={"expiry_warning": "expired"},
                    )
                    session.add(model)
                    session.commit()
            results["expired"] += 1
        elif trial_end < warning_ts:
            # Expiring soon
            hours_left = max(0, (trial_end - now_ts) // 3600)
            with Session(engine) as session:
                model = session.get(AccountModel, overview.account_id)
                if model:
                    model.updated_at = _utcnow()
                    patch_account_graph(
                        session, model,
                        summary_updates={
                            "expiry_warning": f"expiring_in_{hours_left}h",
                            "expiry_warning_hours": hours_left,
                        },
                    )
                    session.add(model)
                    session.commit()
            results["warned"] += 1
        else:
            results["skipped"] += 1

    log(f"Expiry warning: expired {results['expired']}, expiring soon {results['warned']}, "
        f"skipped {results['skipped']}")
    return results


# ---------------------------------------------------------------------------
# ChatGPT token refresh + CPA sync + liveness check
# ---------------------------------------------------------------------------

def refresh_and_sync_cpa(
    *,
    platform: str = "chatgpt",
    limit: int = 200,
    log_fn=None,
) -> dict[str, int]:
    """
    Refresh ChatGPT account tokens, check liveness, and re-upload to CPA.
    - Use session_token to refresh access_token
    - Use /backend-api/me to check liveness
    - Re-generate CPA JSON and upload for live accounts
    - Mark banned accounts as disabled
    """
    log = log_fn or logger.info
    results = {"refreshed": 0, "uploaded": 0, "dead": 0, "skipped": 0, "error": 0}

    from curl_cffi import requests as cffi_requests
    import json
    import base64

    def _decode_jwt(token: str) -> dict:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return {}
            payload = parts[1]
            pad = 4 - len(payload) % 4
            if pad != 4:
                payload += "=" * pad
            return json.loads(base64.urlsafe_b64decode(payload))
        except Exception:
            return {}

    # Load CPA configuration
    try:
        from core.config_store import config_store
        cpa_api_url = config_store.get("cpa_api_url", "")
        cpa_api_key = config_store.get("cpa_api_key", "")
    except Exception:
        cpa_api_url, cpa_api_key = "", ""

    # Get all active ChatGPT accounts
    with Session(engine) as session:
        q = select(AccountModel).where(AccountModel.platform == platform)
        q = q.order_by(AccountModel.created_at.desc()).limit(limit)
        accounts = session.exec(q).all()
        graphs = load_account_graphs(session, [int(a.id) for a in accounts if a.id])

    active_statuses = {"registered", "trial", "subscribed"}

    s = cffi_requests.Session(impersonate="chrome120")
    try:
      for acc in accounts:
        graph = graphs.get(int(acc.id or 0), {})
        if graph.get("lifecycle_status") not in active_statuses:
            results["skipped"] += 1
            continue

        credentials = {
            c["key"]: c["value"]
            for c in (graph.get("credentials") or [])
            if c.get("scope") == "platform"
        }
        session_token = credentials.get("session_token", "")
        if not session_token:
            results["skipped"] += 1
            continue

        try:
            # 1. Use session_token to refresh access_token
            proxy = credentials.get("proxy", None)
            s.proxies = {"http": proxy, "https": proxy} if proxy else {}
            s.cookies.set("__Secure-next-auth.session-token", session_token,
                          domain=".chatgpt.com", path="/")
            resp = s.get("https://chatgpt.com/api/auth/session",
                         headers={"accept": "application/json"}, timeout=30)

            if resp.status_code != 200:
                log(f"  ✗ {acc.email}: session refresh failed HTTP {resp.status_code}")
                results["error"] += 1
                continue

            data = resp.json()
            access_token = data.get("accessToken", "")
            if not access_token:
                log(f"  ✗ {acc.email}: no accessToken")
                results["error"] += 1
                continue

            results["refreshed"] += 1

            # Update credential
            new_session = s.cookies.get("__Secure-next-auth.session-token") or session_token
            credential_updates = {"access_token": access_token}
            if new_session != session_token:
                credential_updates["session_token"] = new_session
            # id_token = access_token (NextAuth has no separate id_token)
            credential_updates["id_token"] = access_token

            with Session(engine) as sess:
                model = sess.get(AccountModel, acc.id)
                if model:
                    model.updated_at = _utcnow()
                    patch_account_graph(
                        sess, model,
                        credential_updates=credential_updates,
                        summary_updates={"last_refresh_at": _utcnow_iso(), "refresh_success": True},
                    )
                    sess.add(model)
                    sess.commit()

            # 2. Check liveness
            check_resp = s.get(
                "https://chatgpt.com/backend-api/me",
                headers={"authorization": f"Bearer {access_token}", "accept": "application/json"},
                timeout=15,
            )

            if check_resp.status_code != 200:
                err_detail = ""
                try:
                    err_detail = str(check_resp.json().get("detail", ""))[:80]
                except Exception:
                    err_detail = check_resp.text[:80]
                log(f"  ✗ {acc.email}: banned ({check_resp.status_code}: {err_detail})")
                results["dead"] += 1
                with Session(engine) as sess:
                    model = sess.get(AccountModel, acc.id)
                    if model:
                        patch_account_graph(
                            sess, model,
                            lifecycle_status=AccountStatus.INVALID.value,
                            summary_updates={"deactivated_at": _utcnow_iso(), "deactivated_reason": err_detail},
                        )
                        sess.add(model)
                        sess.commit()
                continue

            # 3. Upload to CPA
            if cpa_api_url and cpa_api_key:
                from datetime import timedelta
                tz8 = timezone(timedelta(hours=8))
                jwt_payload = _decode_jwt(access_token)
                auth_info = jwt_payload.get("https://api.openai.com/auth", {})
                account_id = auth_info.get("chatgpt_account_id", "")
                exp = jwt_payload.get("exp", 0)
                iat = jwt_payload.get("iat", 0)
                expired_str = datetime.fromtimestamp(exp, tz=tz8).strftime("%Y-%m-%dT%H:%M:%S+08:00") if exp else ""
                last_refresh = datetime.fromtimestamp(iat, tz=tz8).strftime("%Y-%m-%dT%H:%M:%S+08:00") if iat else _utcnow_iso()

                token_data = {
                    "access_token": access_token,
                    "account_id": account_id,
                    "disabled": False,
                    "email": acc.email,
                    "expired": expired_str,
                    "id_token": access_token,
                    "last_refresh": last_refresh,
                    "refresh_token": credentials.get("refresh_token", ""),
                    "type": "codex",
                }

                from urllib.parse import quote
                upload_url = f"{cpa_api_url.rstrip('/')}/v0/management/auth-files?name={quote(acc.email + '.json')}"
                upload_resp = cffi_requests.post(
                    upload_url,
                    headers={"Authorization": f"Bearer {cpa_api_key}", "Content-Type": "application/json"},
                    data=json.dumps(token_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                    verify=False, timeout=30, impersonate="chrome110",
                )
                if upload_resp.status_code in (200, 201, 207):
                    results["uploaded"] += 1
                    log(f"  ✓ {acc.email}: refresh+upload succeeded")
                else:
                    log(f"  ✗ {acc.email}: upload failed HTTP {upload_resp.status_code}")
            else:
                log(f"  ✓ {acc.email}: refresh succeeded (CPA not configured)")

            time.sleep(0.5)

        except Exception as exc:
            results["error"] += 1
            log(f"  ✗ {acc.email}: error {exc}")

    finally:
      s.close()

    log(f"[CPA Sync] refreshed {results['refreshed']}, uploaded {results['uploaded']}, "
        f"banned {results['dead']}, skipped {results['skipped']}, error {results['error']}")
    return results


# ---------------------------------------------------------------------------
# Lifecycle manager (combines all periodic tasks)
# ---------------------------------------------------------------------------

class LifecycleManager:
    """Runs periodic lifecycle tasks in a background thread."""

    def __init__(
        self,
        *,
        check_interval_hours: float = 6,
        refresh_interval_hours: float = 12,
        cpa_sync_interval_hours: float = 6,
        warning_hours: int = 48,
    ):
        self.check_interval = check_interval_hours * 3600
        self.refresh_interval = refresh_interval_hours * 3600
        self.cpa_sync_interval = cpa_sync_interval_hours * 3600
        self.warning_hours = warning_hours
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_check = 0.0
        self._last_refresh = 0.0
        self._last_cpa_sync = 0.0

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="lifecycle-manager")
        self._thread.start()
        print("[LifecycleManager] started")

    def stop(self):
        self._running = False

    def _loop(self):
        # Wait a bit before first run to let the app fully initialize
        time.sleep(LIFECYCLE_STARTUP_DELAY)
        while self._running:
            now = time.time()
            try:
                # Trial expiry warnings — run every cycle
                flag_expiring_trials(hours_warning=self.warning_hours)

                # Validity check
                if now - self._last_check >= self.check_interval:
                    logger.info("Starting account validity check...")
                    check_accounts_validity()
                    self._last_check = now

                # Token refresh
                if now - self._last_refresh >= self.refresh_interval:
                    print("[LifecycleManager] starting token auto-refresh...")
                    refresh_expiring_tokens()
                    self._last_refresh = now

                # CPA sync (refresh token + liveness check + upload)
                if now - self._last_cpa_sync >= self.cpa_sync_interval:
                    print("[LifecycleManager] starting CPA sync (refresh+check+upload)...")
                    refresh_and_sync_cpa()
                    self._last_cpa_sync = now

            except Exception as exc:
                print(f"[LifecycleManager] error: {exc}")

            # Sleep in small increments so stop() is responsive
            for _ in range(60):
                if not self._running:
                    break
                time.sleep(1)


lifecycle_manager = LifecycleManager()
