"""Windsurf registration and account state request wrapper.

HAR shows Windsurf website mainly uses two types of APIs:
  1. /_devin-auth/* JSON APIs for email verification code registration/login
  2. /_backend/exa.* application/proto APIs for querying user, plan and quota

No dependency on full protobuf generated code; only implements lightweight
protobuf wire encoding/decoding needed for current automation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote

from curl_cffi import requests as curl_requests

from core.datetime_utils import _utcnow_iso


WINDSURF_BASE = "https://windsurf.com"
SEAT_SERVICE = "/_backend/exa.seat_management_pb.SeatManagementService"
WINDSURF_TURNSTILE_SITEKEY = "0x4AAAAAAA447Bur1xJStKg5"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _encode_varint(value: int) -> bytes:
    value = int(value)
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value & 0x7F)
    return bytes(out)


def _encode_key(field: int, wire_type: int) -> bytes:
    return _encode_varint((field << 3) | wire_type)


def _field_varint(field: int, value: int | bool) -> bytes:
    return _encode_key(field, 0) + _encode_varint(1 if value is True else int(value))


def _field_bytes(field: int, value: bytes) -> bytes:
    return _encode_key(field, 2) + _encode_varint(len(value)) + value


def _field_string(field: int, value: str) -> bytes:
    return _field_bytes(field, value.encode("utf-8"))


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(buf):
        item = buf[pos]
        pos += 1
        result |= (item & 0x7F) << shift
        if not item & 0x80:
            return result, pos
        shift += 7
    raise ValueError("truncated protobuf varint")


@dataclass(slots=True)
class ProtoField:
    number: int
    wire_type: int
    value: int | bytes

    def as_text(self) -> str:
        if not isinstance(self.value, bytes):
            return ""
        try:
            return self.value.decode("utf-8")
        except UnicodeDecodeError:
            return ""

    def as_message(self) -> list["ProtoField"]:
        if not isinstance(self.value, bytes):
            return []
        try:
            return parse_proto(self.value)
        except Exception:
            return []


def parse_proto(buf: bytes) -> list[ProtoField]:
    fields: list[ProtoField] = []
    pos = 0
    while pos < len(buf):
        key, pos = _read_varint(buf, pos)
        number = key >> 3
        wire_type = key & 0x07
        if wire_type == 0:
            value, pos = _read_varint(buf, pos)
        elif wire_type == 1:
            value = buf[pos:pos + 8]
            pos += 8
        elif wire_type == 2:
            length, pos = _read_varint(buf, pos)
            value = buf[pos:pos + length]
            pos += length
        elif wire_type == 5:
            value = buf[pos:pos + 4]
            pos += 4
        else:
            raise ValueError(f"unsupported protobuf wire type: {wire_type}")
        fields.append(ProtoField(number=number, wire_type=wire_type, value=value))
    return fields


def _first(fields: list[ProtoField], number: int) -> ProtoField | None:
    for item in fields:
        if item.number == number:
            return item
    return None


def _first_text(fields: list[ProtoField], number: int) -> str:
    item = _first(fields, number)
    return item.as_text() if item else ""


def _first_int(fields: list[ProtoField], number: int) -> int:
    item = _first(fields, number)
    return int(item.value) if item and isinstance(item.value, int) else 0


def _first_msg(fields: list[ProtoField], number: int) -> list[ProtoField]:
    item = _first(fields, number)
    return item.as_message() if item else []


def _parse_timestamp_message(fields: list[ProtoField], number: int) -> int:
    item = _first(fields, number)
    if not item:
        return 0
    nested = item.as_message()
    if nested:
        return _first_int(nested, 1)
    return int(item.value) if isinstance(item.value, int) else 0


def _plan_state(plan_name: str) -> str:
    plan = plan_name.strip().lower()
    if not plan:
        return "unknown"
    if "trial" in plan:
        return "trial"
    if plan in {"free", "basic", "starter"}:
        return "free"
    if any(token in plan for token in ("pro", "team", "enterprise", "premium", "ultimate")):
        return "subscribed"
    return plan


def parse_user_message(fields: list[ProtoField]) -> dict[str, Any]:
    return {
        "synthetic_api_key": _first_text(fields, 1),
        "name": _first_text(fields, 2),
        "email": _first_text(fields, 3) or _first_text(fields, 9),
        "user_id": _first_text(fields, 6),
        "team_id": _first_text(fields, 7),
        "role_code": _first_int(fields, 8),
    }


def parse_team_message(fields: list[ProtoField]) -> dict[str, Any]:
    return {
        "team_id": _first_text(fields, 1),
        "team_name": _first_text(fields, 2),
        "plan_code": _first_int(fields, 14),
        "created_at": _parse_timestamp_message(fields, 9),
        "period_start": _parse_timestamp_message(fields, 20),
        "period_end": _parse_timestamp_message(fields, 21),
    }


def parse_plan_message(fields: list[ProtoField]) -> dict[str, Any]:
    plan_name = _first_text(fields, 2)
    return {
        "plan_code": _first_int(fields, 1),
        "plan_name": plan_name,
        "plan_state": _plan_state(plan_name),
        "enabled": bool(_first_int(fields, 3)),
        "is_trial": bool(_first_int(fields, 4)),
        "context_limit": _first_int(fields, 7),
        "daily_limit": _first_int(fields, 8),
        "seat_limit": _first_int(fields, 9),
        "monthly_limit": _first_int(fields, 10),
        "prompt_credits_limit": _first_int(fields, 12),
        "flow_action_credits_limit": _first_int(fields, 13),
    }


def parse_current_user_response(content: bytes) -> dict[str, Any]:
    fields = parse_proto(content)
    user = parse_user_message(_first_msg(fields, 1))
    team = parse_team_message(_first_msg(fields, 4))
    plan = parse_plan_message(_first_msg(fields, 6))
    return {
        "user": user,
        "team": team,
        "plan": plan,
        "role": _first_text(fields, 2),
    }


def parse_post_auth_response(content: bytes) -> dict[str, str]:
    fields = parse_proto(content)
    return {
        "session_token": _first_text(fields, 1),
        "auth_token": _first_text(fields, 3),
        "account_id": _first_text(fields, 4),
        "org_id": _first_text(fields, 5),
    }


def parse_plan_status_response(content: bytes) -> dict[str, Any]:
    fields = parse_proto(content)
    wrapper = _first_msg(fields, 1)
    plan = parse_plan_message(_first_msg(wrapper, 1))
    prompt_limit = _first_int(wrapper, 8) or plan.get("prompt_credits_limit", 0)
    flow_limit = _first_int(wrapper, 9) or plan.get("flow_action_credits_limit", 0)
    prompt_remaining_percent = _first_int(wrapper, 14)
    flow_remaining_percent = _first_int(wrapper, 15)
    return {
        "plan": plan,
        "period_start": _parse_timestamp_message(wrapper, 2),
        "period_end": _parse_timestamp_message(wrapper, 3),
        "prompt_credits_limit": prompt_limit,
        "flow_action_credits_limit": flow_limit,
        "prompt_remaining_percent": prompt_remaining_percent,
        "flow_action_remaining_percent": flow_remaining_percent,
        "cycle_start_at": _first_int(wrapper, 17),
        "cycle_end_at": _first_int(wrapper, 18),
    }


def parse_stripe_subscription_state(content: bytes) -> dict[str, Any]:
    fields = parse_proto(content)
    return {
        "email": _first_text(fields, 1),
        "period_start": _parse_timestamp_message(fields, 5),
        "period_end": _parse_timestamp_message(fields, 6),
        "plan_code": _first_int(fields, 8),
    }


def parse_subscribe_to_plan_response(content: bytes) -> dict[str, str]:
    fields = parse_proto(content)
    return {"checkout_url": _first_text(fields, 1)}


def build_account_overview(
    *,
    current_user: dict[str, Any],
    plan_status: dict[str, Any],
    stripe_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = dict(current_user.get("user") or {})
    team = dict(current_user.get("team") or {})
    plan = dict(plan_status.get("plan") or current_user.get("plan") or {})
    stripe_state = dict(stripe_state or {})
    plan_name = _as_text(plan.get("plan_name") or "unknown")
    plan_state = _as_text(plan.get("plan_state") or _plan_state(plan_name))
    prompt_limit = _as_int(plan_status.get("prompt_credits_limit") or plan.get("prompt_credits_limit"))
    flow_limit = _as_int(plan_status.get("flow_action_credits_limit") or plan.get("flow_action_credits_limit"))
    prompt_remaining = plan_status.get("prompt_remaining_percent")
    flow_remaining = plan_status.get("flow_action_remaining_percent")

    usage_breakdowns = []
    if prompt_limit or prompt_remaining not in (None, ""):
        usage_breakdowns.append({
            "display_name": "Prompt Credits",
            "usage_limit": prompt_limit or "",
            "remaining_usage": f"{prompt_remaining}%" if prompt_remaining not in (None, "") else "",
            "current_usage": f"{max(0, 100 - _as_int(prompt_remaining))}%" if prompt_remaining not in (None, "") else "",
        })
    if flow_limit or flow_remaining not in (None, ""):
        usage_breakdowns.append({
            "display_name": "Flow Action Credits",
            "usage_limit": flow_limit or "",
            "remaining_usage": f"{flow_remaining}%" if flow_remaining not in (None, "") else "",
            "current_usage": f"{max(0, 100 - _as_int(flow_remaining))}%" if flow_remaining not in (None, "") else "",
        })

    chips = [chip for chip in [
        "Active" if user else "",
        plan_name if plan_name and plan_name != "unknown" else "",
        f"Prompt {prompt_remaining}%" if prompt_remaining not in (None, "") else "",
        f"Flow {flow_remaining}%" if flow_remaining not in (None, "") else "",
    ] if chip]

    return {
        "platform": "windsurf",
        "checked_at": _utcnow_iso(),
        "valid": bool(user),
        "remote_email": _as_text(user.get("email") or stripe_state.get("email")),
        "remote_user": user,
        "team": team,
        "team_id": _as_text(team.get("team_id") or user.get("team_id")),
        "team_name": _as_text(team.get("team_name")),
        "plan": plan_name,
        "plan_name": plan_name,
        "plan_state": plan_state,
        "membership_type": plan_name,
        "prompt_credits_limit": prompt_limit,
        "flow_action_credits_limit": flow_limit,
        "prompt_remaining_percent": prompt_remaining,
        "flow_action_remaining_percent": flow_remaining,
        "remaining_credits": " / ".join([
            part for part in [
                f"Prompt {prompt_remaining}%" if prompt_remaining not in (None, "") else "",
                f"Flow {flow_remaining}%" if flow_remaining not in (None, "") else "",
            ] if part
        ]),
        "plan_credits": " / ".join([
            part for part in [
                f"Prompt {prompt_limit}" if prompt_limit else "",
                f"Flow {flow_limit}" if flow_limit else "",
            ] if part
        ]),
        "next_reset_at": _as_int(plan_status.get("cycle_end_at") or plan_status.get("period_end") or stripe_state.get("period_end")),
        "usage_breakdowns": usage_breakdowns,
        "chips": chips,
    }


def summarize_account_state(state: dict[str, Any], *, fallback_email: str = "") -> dict[str, Any]:
    overview = build_account_overview(
        current_user=dict(state.get("current_user") or {}),
        plan_status=dict(state.get("plan_status") or {}),
        stripe_state=dict(state.get("stripe_subscription") or {}),
    )
    if not overview.get("remote_email") and fallback_email:
        overview["remote_email"] = fallback_email
    plan_name = _as_text(overview.get("plan_name") or "unknown")
    message_parts = [f"Current plan: {plan_name}"]
    if overview.get("remaining_credits"):
        message_parts.append(f"Remaining quota: {overview['remaining_credits']}")
    return {
        "valid": bool(overview.get("valid")),
        "message": ", ".join(message_parts),
        "remote_user": overview.get("remote_user", {}),
        "team": overview.get("team", {}),
        "membership_type": plan_name,
        "plan": plan_name,
        "plan_name": plan_name,
        "plan_state": overview.get("plan_state", "unknown"),
        "remaining_credits": overview.get("remaining_credits", ""),
        "plan_credits": overview.get("plan_credits", ""),
        "next_reset_at": overview.get("next_reset_at", 0),
        "usage_breakdowns": overview.get("usage_breakdowns", []),
        "prompt_credits_limit": overview.get("prompt_credits_limit", 0),
        "flow_action_credits_limit": overview.get("flow_action_credits_limit", 0),
        "prompt_remaining_percent": overview.get("prompt_remaining_percent"),
        "flow_action_remaining_percent": overview.get("flow_action_remaining_percent"),
        "account_overview": overview,
    }


def extract_windsurf_account_context(account: Any) -> dict[str, str]:
    extra = dict(getattr(account, "extra", {}) or {})
    overview = dict(extra.get("account_overview") or {})
    legacy_extra = dict(overview.get("legacy_extra") or {})
    return {
        "session_token": _as_text(
            extra.get("session_token")
            or extra.get("sessionToken")
            or extra.get("legacy_token")
            or legacy_extra.get("session_token")
            or getattr(account, "token", "")
        ),
        "auth_token": _as_text(extra.get("auth_token") or extra.get("authToken") or legacy_extra.get("auth_token")),
        "account_id": _as_text(extra.get("account_id") or extra.get("accountId") or legacy_extra.get("account_id")),
        "org_id": _as_text(extra.get("org_id") or extra.get("orgId") or legacy_extra.get("org_id")),
    }


class WindsurfClient:
    def __init__(self, *, proxy: str | None = None, log_fn: Callable[[str], None] = print):
        self.s = curl_requests.Session()
        self.s.impersonate = "chrome131"
        if proxy:
            self.s.proxies = {"http": proxy, "https": proxy}
        self.s.headers.update({
            "user-agent": UA,
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "dnt": "1",
        })
        self.log = log_fn

    def _json_post(self, path: str, payload: dict[str, Any], *, referer: str = "/account/register") -> dict[str, Any]:
        response = self.s.post(
            f"{WINDSURF_BASE}{path}",
            json=payload,
            headers={
                "accept": "*/*",
                "content-type": "application/json",
                "origin": WINDSURF_BASE,
                "referer": f"{WINDSURF_BASE}{referer}",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"{path} failed: HTTP {response.status_code} {response.text[:200]}")
        data = response.json()
        if isinstance(data, dict):
            return data
        raise RuntimeError(f"{path} returned abnormal format")

    def _proto_post(
        self,
        method: str,
        body: bytes,
        *,
        account_id: str = "",
        org_id: str = "",
        session_token: str = "",
        auth1_token: str = "",
        referer: str = "/profile",
    ) -> bytes:
        headers = {
            "accept": "*/*",
            "content-type": "application/proto",
            "connect-protocol-version": "1",
            "origin": WINDSURF_BASE,
            "referer": f"{WINDSURF_BASE}{referer}",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
        }
        if account_id:
            headers["x-devin-account-id"] = account_id
        if org_id:
            headers["x-devin-primary-org-id"] = org_id
        if session_token:
            headers["x-devin-session-token"] = session_token
            headers["x-auth-token"] = session_token
        if auth1_token:
            headers["x-devin-auth1-token"] = auth1_token
        response = self.s.post(
            f"{WINDSURF_BASE}{SEAT_SERVICE}/{method}",
            data=body,
            headers=headers,
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"{method} failed: HTTP {response.status_code} {response.text[:200]}")
        return bytes(response.content or b"")

    def check_user_login_method(self, email: str) -> None:
        self._proto_post("CheckUserLoginMethod", _field_string(1, email), referer="/account/register")

    def fetch_connections(self, email: str) -> dict[str, Any]:
        return self._json_post("/_devin-auth/connections", {"product": "windsurf", "email": email})

    def start_email_signup(self, email: str) -> str:
        self.log(f"Step1: Sending Windsurf verification code to {email}")
        data = self._json_post(
            "/_devin-auth/email/start",
            {"email": email, "mode": "signup", "product": "Windsurf"},
        )
        token = _as_text(data.get("email_verification_token"))
        if not token:
            raise RuntimeError("Windsurf did not return email_verification_token")
        return token

    def complete_email_signup(self, *, email: str, verification_token: str, code: str, password: str, name: str) -> dict[str, Any]:
        self.log("Step2: Submitting Windsurf email verification code")
        data = self._json_post(
            "/_devin-auth/email/complete",
            {
                "email_verification_token": verification_token,
                "code": code,
                "mode": "signup",
                "password": password,
                "name": name,
            },
        )
        auth_token = _as_text(data.get("token"))
        if not auth_token:
            raise RuntimeError("Windsurf did not return auth token")
        return data

    def login_with_password(self, email: str, password: str) -> dict[str, str]:
        """Log in to existing account with email+password, returns session_token etc."""
        self.log(f"Password login Windsurf: {email}")
        start_data = self._json_post(
            "/_devin-auth/email/start",
            {"email": email, "mode": "login", "product": "Windsurf"},
        )
        verification_token = _as_text(start_data.get("email_verification_token"))
        if not verification_token:
            raise RuntimeError("Windsurf login did not return email_verification_token")
        data = self._json_post(
            "/_devin-auth/email/complete",
            {
                "email_verification_token": verification_token,
                "mode": "login",
                "password": password,
            },
        )
        auth_token = _as_text(data.get("token"))
        if not auth_token:
            raise RuntimeError("Windsurf password login did not return auth token")
        return self.post_auth(auth_token)

    def post_auth(self, auth_token: str) -> dict[str, str]:
        self.log("Step3: Exchanging Windsurf session")
        content = self._proto_post(
            "WindsurfPostAuth",
            _field_string(1, auth_token),
            referer="/account/register",
        )
        data = parse_post_auth_response(content)
        if not data.get("session_token"):
            raise RuntimeError("Windsurf did not return session_token")
        return data

    def _auth_body(self, session_token: str, *, include_plan_status_flag: bool = False) -> bytes:
        body = _field_string(1, session_token)
        if include_plan_status_flag:
            body += _field_varint(2, 1)
        return body

    def get_current_user(self, session_token: str, *, account_id: str = "", org_id: str = "") -> dict[str, Any]:
        content = self._proto_post(
            "GetCurrentUser",
            self._auth_body(session_token),
            account_id=account_id,
            org_id=org_id,
        )
        return parse_current_user_response(content)

    def get_plan_status(self, session_token: str, *, account_id: str = "", org_id: str = "") -> dict[str, Any]:
        content = self._proto_post(
            "GetPlanStatus",
            self._auth_body(session_token, include_plan_status_flag=True),
            account_id=account_id,
            org_id=org_id,
            referer="/subscription/usage",
        )
        return parse_plan_status_response(content)

    def get_stripe_subscription_state(self, session_token: str, *, account_id: str = "", org_id: str = "") -> dict[str, Any]:
        content = self._proto_post(
            "GetStripeSubscriptionState",
            self._auth_body(session_token),
            account_id=account_id,
            org_id=org_id,
            referer="/subscription/manage-plan",
        )
        return parse_stripe_subscription_state(content)

    def check_pro_trial_eligibility(self, session_token: str, *, account_id: str = "", org_id: str = "") -> bool:
        content = self._proto_post(
            "CheckProTrialEligibility",
            self._auth_body(session_token),
            account_id=account_id,
            org_id=org_id,
            referer="/pricing",
        )
        fields = parse_proto(content)
        return bool(_first_int(fields, 1))

    def subscribe_to_plan(
        self,
        session_token: str,
        *,
        account_id: str = "",
        org_id: str = "",
        auth1_token: str = "",
        turnstile_token: str,
        success_url: str = "",
        cancel_url: str = "",
    ) -> dict[str, str]:
        token = _as_text(turnstile_token)
        if not token:
            raise RuntimeError("Missing Turnstile token, cannot call Windsurf SubscribeToPlan")
        success = success_url or f"{WINDSURF_BASE}/subscription/pending?expect_tier=trial"
        cancel = cancel_url or f"{WINDSURF_BASE}/plan?plan_cancelled=true&plan_tier=trial"
        billing_referer = f"/billing/individual?plan=9&turnstile_token={quote(token, safe='')}"
        body = b"".join([
            _field_string(1, session_token),
            _field_varint(3, 1),
            _field_string(4, success),
            _field_string(5, cancel),
            _field_varint(8, 2),
            _field_varint(9, 1),
            _field_string(10, token),
        ])
        content = self._proto_post(
            "SubscribeToPlan",
            body,
            account_id=account_id,
            org_id=org_id,
            session_token=session_token,
            auth1_token=auth1_token,
            referer=billing_referer,
        )
        result = parse_subscribe_to_plan_response(content)
        if not result.get("checkout_url"):
            raise RuntimeError("Windsurf SubscribeToPlan did not return checkout_url")
        return result

    def load_account_state(self, *, session_token: str, account_id: str = "", org_id: str = "", fallback_email: str = "") -> dict[str, Any]:
        if not session_token:
            raise RuntimeError("Account missing Windsurf session_token")
        current_user = self.get_current_user(session_token, account_id=account_id, org_id=org_id)
        plan_status = self.get_plan_status(session_token, account_id=account_id, org_id=org_id)
        stripe_state: dict[str, Any] = {}
        try:
            stripe_state = self.get_stripe_subscription_state(session_token, account_id=account_id, org_id=org_id)
        except Exception as exc:
            stripe_state = {"error": str(exc)}
        state = {
            "current_user": current_user,
            "plan_status": plan_status,
            "stripe_subscription": stripe_state,
        }
        state["summary"] = summarize_account_state(state, fallback_email=fallback_email)
        return state


def load_windsurf_account_state(
    account: Any,
    *,
    proxy: str | None = None,
    log_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    context = extract_windsurf_account_context(account)
    client = WindsurfClient(proxy=proxy, log_fn=log_fn)
    return client.load_account_state(
        session_token=context["session_token"],
        account_id=context["account_id"],
        org_id=context["org_id"],
        fallback_email=getattr(account, "email", ""),
    )
