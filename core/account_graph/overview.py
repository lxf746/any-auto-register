from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from core.datetime_utils import ensure_utc_datetime, serialize_datetime


PLATFORM_CREDENTIAL_TYPES: dict[str, str] = {
    "legacy_token": "token",
    "access_token": "token",
    "refresh_token": "token",
    "firebase_refresh_token": "token",
    "session_token": "token",
    "session_cookie": "cookie",
    "id_token": "token",
    "client_id": "identifier",
    "client_secret": "secret",
    "workspace_id": "identifier",
    "workspace_slug": "identifier",
    "customer_id": "identifier",
    "referral_code": "identifier",
    "account_id": "identifier",
    "org_id": "identifier",
    "auth_token": "token",
    "accessToken": "token",
    "refreshToken": "token",
    "sessionToken": "token",
    "idToken": "token",
    "clientId": "identifier",
    "clientSecret": "secret",
    "workspaceId": "identifier",
    "accountId": "identifier",
    "orgId": "identifier",
    "authToken": "token",
    "cookies": "cookie",
    "cookie": "cookie",
    "api_key": "secret",
    "wos_session": "token",
    "sso": "cookie",
    "sso_rw": "cookie",
}

PRIMARY_TOKEN_WRITE_KEYS: dict[str, str] = {
    "cursor": "session_token",
    "chatgpt": "access_token",
    "kiro": "accessToken",
    "trae": "legacy_token",
    "blink": "firebase_refresh_token",
    "openblocklabs": "wos_session",
}

NON_LEGACY_EXTRA_KEYS = {
    "account_overview",
    "provider_accounts",
    "provider_resources",
    "identity",
    "verification_mailbox",
    "cashier_url",
    "region",
    "trial_end_time",
}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _preview_secret(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if len(text) <= 10:
        return text
    return f"{text[:6]}...{text[-4:]}"


def _dedupe_chips(*groups: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for item in group or []:
            chip = _text(item)
            if not chip or chip == "local not switched" or chip in seen:
                continue
            seen.add(chip)
            result.append(chip)
    return result


def _normalize_plan_state(value: Any) -> str:
    raw = _text(value).lower()
    if not raw:
        return ""
    if raw in {"trial", "trialing", "free_trial", "trial-active", "trial_active"}:
        return "trial"
    if raw in {"expired", "cancelled", "canceled", "inactive", "ended"}:
        return "expired"
    if raw in {"free", "basic", "starter", "hobby"}:
        return "free"
    if raw in {"eligible", "trial_eligible"}:
        return "eligible"
    subscribed_hints = (
        "pro",
        "plus",
        "premium",
        "paid",
        "student",
        "team",
        "business",
        "enterprise",
        "member",
    )
    if any(token in raw for token in subscribed_hints):
        return "subscribed"
    return raw


def _derive_plan_name(overview: dict[str, Any]) -> str:
    return _text(
        overview.get("plan_name")
        or overview.get("plan")
        or overview.get("membership_type")
        or overview.get("individual_membership_type")
    )


def _derive_validity_status(lifecycle_status: str, overview: dict[str, Any]) -> str:
    if lifecycle_status == "invalid":
        return "invalid"
    if "valid" in overview:
        return "valid" if bool(overview.get("valid")) else "invalid"
    return "unknown"


def _derive_plan_state(
    lifecycle_status: str,
    overview: dict[str, Any],
    trial_end_time: int,
) -> str:
    explicit = _normalize_plan_state(overview.get("plan_state"))
    if explicit:
        return explicit

    candidates = [
        overview.get("membership_type"),
        overview.get("plan"),
        overview.get("plan_name"),
    ]
    for candidate in candidates:
        normalized = _normalize_plan_state(candidate)
        if normalized:
            return normalized

    if lifecycle_status in {"trial", "subscribed", "expired"}:
        return lifecycle_status
    if overview.get("trial_eligible") and not trial_end_time:
        return "eligible"
    return "unknown"


def _derive_display_status(
    lifecycle_status: str,
    validity_status: str,
    plan_state: str,
) -> str:
    if validity_status == "invalid":
        return "invalid"
    if plan_state == "expired" or lifecycle_status == "expired":
        return "expired"
    if plan_state == "subscribed":
        return "subscribed"
    if plan_state == "trial":
        return "trial"
    return lifecycle_status or "registered"


def recover_lifecycle_status_for_valid_account(graph: dict[str, Any]) -> str:
    """Recover the active lifecycle state for an account that re-validated."""
    lifecycle_status = _text(
        graph.get("lifecycle_status") or _safe_dict(graph.get("overview")).get("lifecycle_status")
    )
    if lifecycle_status and lifecycle_status != "invalid":
        return lifecycle_status

    plan_state = _normalize_plan_state(
        graph.get("plan_state") or _safe_dict(graph.get("overview")).get("plan_state")
    )
    if plan_state in {"trial", "subscribed", "expired"}:
        return plan_state
    return "registered"


def _parse_checked_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return ensure_utc_datetime(value)
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            base = normalized[:-1]
            if len(base) >= 6 and base[-6] in {"+", "-"} and base[-3] == ":":
                normalized = base
            else:
                normalized = f"{base}+00:00"
        try:
            return ensure_utc_datetime(datetime.fromisoformat(normalized))
        except ValueError:
            return None
    return None


def _normalize_overview_summary(
    *,
    platform: str,
    lifecycle_status: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    payload = _safe_dict(summary)
    payload["platform"] = platform

    trial_end_time = int(payload.get("trial_end_time") or 0)
    payload["trial_end_time"] = trial_end_time
    payload["cashier_url"] = _text(payload.get("cashier_url"))
    payload["region"] = _text(payload.get("region"))

    validity_status = _derive_validity_status(lifecycle_status, payload)
    plan_state = _derive_plan_state(lifecycle_status, payload, trial_end_time)
    plan_name = _derive_plan_name(payload)
    display_status = _derive_display_status(lifecycle_status, validity_status, plan_state)

    payload["chips"] = _dedupe_chips(payload.get("chips") or [])
    if bool(payload.get("local_matches_target")) and "current" not in payload["chips"]:
        payload["chips"].append("current")

    payload.update(
        {
            "lifecycle_status": lifecycle_status,
            "validity_status": validity_status,
            "plan_state": plan_state,
            "plan_name": plan_name,
            "display_status": display_status,
        }
    )
    payload["remote_email"] = _text(payload.get("remote_email"))
    checked_at = payload.get("checked_at")
    if isinstance(checked_at, datetime):
        payload["checked_at"] = serialize_datetime(checked_at)
    elif checked_at is not None:
        payload["checked_at"] = checked_at
    return payload


def matches_status_filter(graph: dict[str, Any], status: str) -> bool:
    expected = _text(status)
    if not expected:
        return True
    return expected in {
        _text(graph.get("display_status")),
        _text(graph.get("lifecycle_status")),
        _text(graph.get("plan_state")),
        _text(graph.get("validity_status")),
    }


def compute_account_stats(graphs: list[dict[str, Any]], platforms: list[str]) -> dict[str, dict[str, int]]:
    by_platform: dict[str, int] = defaultdict(int)
    by_lifecycle_status: dict[str, int] = defaultdict(int)
    by_plan_state: dict[str, int] = defaultdict(int)
    by_validity_status: dict[str, int] = defaultdict(int)
    by_display_status: dict[str, int] = defaultdict(int)

    for platform in platforms:
        by_platform[platform] += 1
    for graph in graphs:
        by_lifecycle_status[_text(graph.get("lifecycle_status") or "registered")] += 1
        by_plan_state[_text(graph.get("plan_state") or "unknown")] += 1
        by_validity_status[_text(graph.get("validity_status") or "unknown")] += 1
        by_display_status[_text(graph.get("display_status") or "registered")] += 1

    return {
        "by_platform": dict(by_platform),
        "by_lifecycle_status": dict(by_lifecycle_status),
        "by_plan_state": dict(by_plan_state),
        "by_validity_status": dict(by_validity_status),
        "by_display_status": dict(by_display_status),
    }
