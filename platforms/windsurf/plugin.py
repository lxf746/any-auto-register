"""Windsurf platform plugin."""
from __future__ import annotations

import random

from core.mailbox.base import BaseMailbox
from core.base_platform import Account, AccountStatus, BasePlatform, RegisterConfig
from core.registration import BrowserRegistrationAdapter, OtpSpec, ProtocolMailboxAdapter, RegistrationResult
from core.registration.helpers import resolve_timeout
from core.registry import register
from platforms.windsurf.core import load_windsurf_account_state


def _status_from_overview(overview: dict) -> AccountStatus:
    plan_state = str((overview or {}).get("plan_state") or "").strip().lower()
    if plan_state == "subscribed":
        return AccountStatus.SUBSCRIBED
    if plan_state == "trial":
        return AccountStatus.TRIAL
    if plan_state == "free":
        return AccountStatus.REGISTERED
    if plan_state == "expired":
        return AccountStatus.EXPIRED
    return AccountStatus.REGISTERED


def _default_name(email: str) -> str:
    local = (email or "").split("@", 1)[0].strip()
    cleaned = "".join(ch if ch.isalpha() else " " for ch in local).strip()
    if cleaned:
        return " ".join(part.capitalize() for part in cleaned.split()[:2])
    return "Windsurf User"


@register
class WindsurfPlatform(BasePlatform):
    name = "windsurf"
    display_name = "Windsurf"
    version = "1.0.0"
    supported_executors = ["protocol", "headless", "headed"]
    supported_identity_modes = ["mailbox"]
    protocol_captcha_order = ("2captcha", "capsolver", "auto")
    capabilities = [
        "query_state",              # Query account state/quota
        "check_trial",              # Check Pro Trial eligibility
        "generate_link",            # Generate Pro Trial Stripe link (auto captcha)
        "generate_link_browser",    # Generate Pro Trial Stripe link (browser)
        "switch_desktop",           # Switch to desktop app
    ]
    capability_overrides = {
        "generate_link": {
            "label": "Generate Pro Trial Link (Auto Captcha)",
            "params": [
                {"key": "turnstile_token", "label": "Turnstile Token (optional, auto captcha)", "type": "text"},
            ],
        },
        "generate_link_browser": {
            "label": "Generate Pro Trial Link (Browser)",
            "params": [
                {"key": "turnstile_token", "label": "Turnstile Token (optional, auto captcha)", "type": "text"},
                {"key": "timeout", "label": "Wait seconds (default 180)", "type": "number"},
                {"key": "headless", "label": "Headless mode", "type": "text", "options": ["false", "true"]},
            ],
            "sync": False,
        },
        "switch_desktop": {
            "label": "Switch Desktop App (Pure Protocol)",
        },
    }

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _map_windsurf_result(self, result: dict) -> RegistrationResult:
        overview = dict(result.get("account_overview") or {})
        return RegistrationResult(
            email=result["email"],
            password=result.get("password", ""),
            user_id=result.get("user_id", ""),
            token=result.get("session_token", ""),
            status=_status_from_overview(overview),
            extra={
                "name": result.get("name", ""),
                "auth_token": result.get("auth_token", ""),
                "session_token": result.get("session_token", ""),
                "account_id": result.get("account_id", ""),
                "org_id": result.get("org_id", ""),
                "account_overview": overview,
                "state_summary": result.get("state_summary", {}),
            },
        )

    def build_protocol_mailbox_adapter(self):
        def _build_worker(ctx, artifacts):
            from platforms.windsurf.protocol_mailbox import WindsurfProtocolMailboxWorker

            return WindsurfProtocolMailboxWorker(proxy=ctx.proxy, log_fn=ctx.log)

        def _run_worker(worker, ctx, artifacts):
            return worker.run(
                email=ctx.identity.email,
                password=ctx.password or "",
                name=str(ctx.extra.get("name") or _default_name(ctx.identity.email)),
                otp_callback=artifacts.otp_callback,
            )

        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_windsurf_result(result),
            worker_builder=_build_worker,
            register_runner=_run_worker,
            otp_spec=OtpSpec(
                keyword="Windsurf",
                code_pattern=r"\b(\d{6})\b",
                wait_message="Waiting for Windsurf email verification code...",
                success_label="Verification code",
                timeout=resolve_timeout(self.config.extra or {}, ("otp_timeout",), 120),
            ),
        )

    def build_browser_registration_adapter(self):
        def _build_worker(ctx, artifacts):
            from platforms.windsurf.browser_register import WindsurfBrowserRegister

            return WindsurfBrowserRegister(
                headless=(ctx.executor_type == "headless"),
                proxy=ctx.proxy,
                otp_callback=artifacts.otp_callback,
                log_fn=ctx.log,
            )

        def _run_worker(worker, ctx, artifacts):
            return worker.run(
                email=ctx.identity.email,
                password=ctx.password or "",
                name=str(ctx.extra.get("name") or _default_name(ctx.identity.email)),
            )

        return BrowserRegistrationAdapter(
            result_mapper=lambda ctx, result: self._map_windsurf_result(result),
            browser_worker_builder=_build_worker,
            browser_register_runner=_run_worker,
            otp_spec=OtpSpec(
                keyword="Windsurf",
                code_pattern=r"\b(\d{6})\b",
                wait_message="Waiting for Windsurf email verification code...",
                success_label="Verification code",
                timeout=resolve_timeout(self.config.extra or {}, ("otp_timeout",), 120),
            ),
        )

    def _load_state(self, account: Account) -> dict:
        return load_windsurf_account_state(
            account,
            proxy=self.config.proxy if self.config else None,
            log_fn=self.log,
        )

    def check_valid(self, account: Account) -> bool:
        try:
            state = self._load_state(account)
        except Exception:
            self._last_check_overview = {}
            return False
        summary = dict(state.get("summary") or {})
        overview = dict(summary.get("account_overview") or {})
        self._last_check_overview = overview
        return bool(summary.get("valid"))

    def get_last_check_overview(self) -> dict:
        return dict(getattr(self, "_last_check_overview", {}) or {})

    def get_desktop_state(self) -> dict:
        from platforms.windsurf.switch import get_windsurf_desktop_state

        return get_windsurf_desktop_state()

    def _handle_switch_desktop(self, account: Account, params: dict) -> dict:
        """
        Handle switch_desktop capability for Windsurf.

        Pure protocol implementation:
        1. Use session_token to call GetOneTimeAuthToken → get OTT
        2. Pass to Windsurf via windsurf:// deep link → complete authentication switch
        """
        from platforms.windsurf.core import extract_windsurf_account_context
        from platforms.windsurf.switch import (
            get_windsurf_desktop_state,
            switch_windsurf_account,
        )

        context = extract_windsurf_account_context(account)
        session_token = context["session_token"]
        if not session_token:
            return {"ok": False, "error": "Account missing session_token"}

        self.log(f"Switching to: {account.email}")
        proxy = self.config.proxy if self.config else None
        ok, msg = switch_windsurf_account(session_token=session_token, proxy=proxy)

        if not ok:
            return {"ok": False, "error": msg}

        return {
            "ok": True,
            "data": {
                "message": msg,
                "email": account.email,
                "desktop_app_state": get_windsurf_desktop_state(),
            },
        }

    def _handle_generate_link_browser(self, account: Account, params: dict) -> dict:
        """Handle generate_link_browser capability for Windsurf."""
        if not str(account.password or "").strip():
            return {"ok": False, "error": "Account missing Windsurf password, cannot execute browser automation"}

        turnstile_token = str(params.get("turnstile_token") or "").strip()
        if turnstile_token:
            self.log("Using provided Turnstile token as browser flow fallback")
        else:
            self.log("Turnstile token not provided, will auto-verify on page")
        headless_param = params.get("headless")
        if headless_param in (None, ""):
            headless = self.config.executor_type == "headless"
        else:
            headless = str(headless_param).strip().lower() not in {"0", "false", "no", "off", "not"}

        from platforms.windsurf.browser_register import generate_checkout_link_via_windsurf_ui

        result = generate_checkout_link_via_windsurf_ui(
            email=str(account.email or ""),
            password=str(account.password or ""),
            turnstile_token=turnstile_token,
            timeout=int(params.get("timeout") or 180),
            proxy=self.config.proxy if self.config else None,
            headless=headless,
            log_fn=self.log,
        )
        return {
            "ok": True,
            "data": {
                **result,
                "message": "Windsurf Pro Trial Stripe link generated",
            },
        }

    def _handle_query_state(self, account: Account, params: dict) -> dict:
        """Handle query_state capability for Windsurf."""
        state = self._load_state(account)
        summary = dict(state.get("summary") or {})
        overview = dict(summary.get("account_overview") or {})
        return {
            "ok": True,
            "data": {
                **summary,
                "account_overview": overview,
                "quota_note": "Windsurf quota from website application/proto interface; currently parsing Prompt Credits and Flow Action Credits limits and remaining percentages.",
            },
        }

    def _handle_check_trial(self, account: Account, params: dict) -> dict:
        """Handle check_trial capability for Windsurf."""
        from platforms.windsurf.core import WindsurfClient, extract_windsurf_account_context

        context = extract_windsurf_account_context(account)
        if not context["session_token"]:
            return {"ok": False, "error": "Account missing Windsurf session_token"}
        client = WindsurfClient(proxy=self.config.proxy if self.config else None, log_fn=self.log)
        eligible = client.check_pro_trial_eligibility(
            context["session_token"],
            account_id=context["account_id"],
            org_id=context["org_id"],
        )
        return {"ok": True, "data": {"trial_eligible": eligible, "message": "Eligible" if eligible else "Not eligible"}}

    def _handle_generate_link(self, account: Account, params: dict) -> dict:
        """Handle generate_link capability for Windsurf."""
        from platforms.windsurf.core import WINDSURF_TURNSTILE_SITEKEY, WINDSURF_BASE, WindsurfClient, extract_windsurf_account_context

        context = extract_windsurf_account_context(account)
        if not context["session_token"]:
            return {"ok": False, "error": "Account missing Windsurf session_token"}

        turnstile_token = str(params.get("turnstile_token") or "").strip()
        if not turnstile_token:
            try:
                self.log("Auto-getting Windsurf Turnstile token...")
                turnstile_token = self.solve_turnstile_with_fallback(
                    f"{WINDSURF_BASE}/pricing",
                    WINDSURF_TURNSTILE_SITEKEY,
                )
            except Exception as exc:
                return {
                    "ok": False,
                    "error": (
                        "Generating Windsurf Pro Trial link requires Turnstile token."
                        f"Auto-solve failed: {exc}."
                        "You can manually fill turnstile_token in action parameters, or use browser-assisted generation."
                    ),
                }

        client = WindsurfClient(proxy=self.config.proxy if self.config else None, log_fn=self.log)
        trial_eligible = False
        try:
            trial_eligible = client.check_pro_trial_eligibility(
                context["session_token"],
                account_id=context["account_id"],
                org_id=context["org_id"],
            )
        except Exception as exc:
            self.log(f"Windsurf trial eligibility check failed, continuing with link generation: {exc}")

        refreshed_auth: dict[str, str] = {}
        try:
            checkout = client.subscribe_to_plan(
                context["session_token"],
                account_id=context["account_id"],
                org_id=context["org_id"],
                auth1_token=context.get("auth_token", ""),
                turnstile_token=turnstile_token,
            )
        except RuntimeError as exc:
            if "HTTP 401" not in str(exc):
                raise
            self.log("Windsurf SubscribeToPlan returned 401, attempting session refresh...")
            # 1) Try auth_token refresh first
            if context.get("auth_token"):
                try:
                    refreshed_auth = client.post_auth(context["auth_token"])
                except Exception as re_exc:
                    self.log(f"auth_token refresh failed: {re_exc}")
            # 2) If auth_token also fails, re-login with password
            if not refreshed_auth.get("session_token") and str(getattr(account, 'password', '') or '').strip():
                self.log("auth_token refresh failed, attempting password re-login...")
                try:
                    refreshed_auth = client.login_with_password(
                        str(account.email or ""),
                        str(account.password),
                    )
                except Exception as login_exc:
                    self.log(f"Password login also failed: {login_exc}")
            if not refreshed_auth.get("session_token"):
                raise RuntimeError(f"Windsurf session refresh failed, original error: {exc}") from exc
            checkout = client.subscribe_to_plan(
                refreshed_auth["session_token"],
                account_id=refreshed_auth.get("account_id", "") or context["account_id"],
                org_id=refreshed_auth.get("org_id", "") or context["org_id"],
                auth1_token=refreshed_auth.get("auth_token", "") or context.get("auth_token", ""),
                turnstile_token=turnstile_token,
            )
        checkout_url = str(checkout.get("checkout_url") or "").strip()
        payment_channel = "checkout"
        cashier_url = checkout_url
        extra_payload: dict = {}
        refreshed_credentials = {
            key: value
            for key, value in {
                "session_token": refreshed_auth.get("session_token", "") or context.get("session_token", ""),
                "account_id": refreshed_auth.get("account_id", "") or context.get("account_id", ""),
                "org_id": refreshed_auth.get("org_id", "") or context.get("org_id", ""),
                "auth_token": refreshed_auth.get("auth_token", "") or context.get("auth_token", ""),
            }.items()
            if value
        }
        return {
            "ok": True,
            "data": {
                "url": cashier_url,
                "cashier_url": cashier_url,
                "checkout_url": checkout_url,
                "payment_channel": payment_channel,
                "trial_eligible": trial_eligible,
                "session_refreshed": bool(refreshed_auth),
                **refreshed_credentials,
                **extra_payload,
                "message": "Windsurf Pro Trial Stripe link generated",
            },
        }

    
    def get_quota(self, account: Account) -> dict:
        state = self._load_state(account)
        return dict((state.get("summary") or {}).get("account_overview") or {})
