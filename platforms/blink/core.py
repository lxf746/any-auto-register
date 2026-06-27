"""
blink.new registration and account state request wrapper.

Core flow:
  1. POST /api/auth/main-app/magic-link send magic link
  2. GET /api/auth/main-app/magic-link redeem customToken
  3. POST Firebase signInWithCustomToken get idToken / firebase refresh token
  4. POST /api/auth/token get Blink access_token / refresh_token
  5. POST /api/auth/session get Blink session cookie
  6. POST /api/users/create initialize user record
  7. POST /api/credits/migrate and /api/referral/generate complete post-registration actions
  8. GET /api/auth/session-data query plan/quota
  9. POST /api/stripe/checkout generate Stripe Checkout link
"""
from __future__ import annotations

from typing import Any, Callable

from curl_cffi import requests as curl_requests

from core.mixins.managed_session import ManagedSession

BLINK_BASE = "https://blink.new"
FIREBASE_API_KEY = "test"
FIREBASE_SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_API_KEY}"
FIREBASE_REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
FIREBASE_CLIENT_VERSION = "Chrome/JsCore/11.10.0/FirebaseCore-web"
FIREBASE_GMP_ID = "1:179867881115:web:08cc80113a7cb5f152003e"
BLINK_PRICE_IDS = {
    "pro": "price_1S2oW1IChkSeVZoQl1420r64",
}
_SUBSCRIBED_TIERS = {"pro", "team", "business", "enterprise"}

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _unwrap_firestore_seconds(value: Any) -> int:
    if isinstance(value, dict):
        return _as_int(value.get("_seconds"))
    return _as_int(value)


def _derive_plan_state(tier: str) -> str:
    normalized = tier.strip().lower()
    if not normalized:
        return "unknown"
    if normalized in _SUBSCRIBED_TIERS:
        return "subscribed"
    if normalized in {"trial", "trialing"}:
        return "trial"
    if normalized in {"free", "starter", "basic", "hobby"}:
        return "free"
    return normalized


def build_blink_account_overview(session_data: dict[str, Any], *, fallback_email: str = "") -> dict[str, Any]:
    user = _as_dict(session_data.get("user"))
    workspace = _as_dict(session_data.get("workspace"))
    usage = _as_dict(user.get("usage") or workspace.get("usage"))
    tier = _as_text(workspace.get("tier") or workspace.get("plan_type") or "free")
    plan_state = _derive_plan_state(tier)

    chips: list[str] = []
    if workspace.get("is_personal"):
        chips.append("Personal")
    if tier:
        chips.append(tier.upper())
    billing_limit = _as_int(usage.get("billing_period_credits_limit"))
    daily_limit = _as_int(usage.get("daily_credits_limit"))
    monthly_limit = _as_int(usage.get("monthly_credits_limit"))
    if billing_limit:
        chips.append(f"Billing period quota {billing_limit}")
    elif monthly_limit:
        chips.append(f"Monthly quota {monthly_limit}")
    if daily_limit:
        chips.append(f"Daily quota {daily_limit}")

    geoip = _as_dict(user.get("geoip"))
    return {
        "remote_email": _as_text(user.get("email") or fallback_email),
        "workspace_id": _as_text(workspace.get("id")),
        "workspace_slug": _as_text(workspace.get("slug")),
        "workspace_name": _as_text(workspace.get("name")),
        "customer_id": _as_text(user.get("customer_id") or workspace.get("customer_id")),
        "plan": tier,
        "plan_name": tier,
        "plan_state": plan_state,
        "membership_type": tier,
        "plan_type": _as_text(workspace.get("plan_type")),
        "is_personal": bool(workspace.get("is_personal")),
        "member_count": _as_int(workspace.get("member_count")),
        "cancel_at_period_end": bool(workspace.get("cancel_at_period_end")),
        "cancel_at": _as_text(workspace.get("cancel_at")),
        "referral_code": _as_text(workspace.get("referral_code") or user.get("referral_code")),
        "daily_credits_used": _as_int(usage.get("daily_credits_used")),
        "daily_credits_limit": daily_limit,
        "monthly_credits_used": _as_int(usage.get("monthly_credits_used")),
        "monthly_credits_limit": monthly_limit,
        "billing_period_credits_used": _as_int(usage.get("billing_period_credits_used")),
        "billing_period_credits_limit": billing_limit,
        "billing_period_start": _unwrap_firestore_seconds(usage.get("billing_period_start")),
        "billing_period_end": _unwrap_firestore_seconds(usage.get("billing_period_end")),
        "enable_usage_based_pricing": bool(usage.get("enable_usage_based_pricing")),
        "geo_country_code": _as_text(geoip.get("country_code")),
        "geo_country_name": _as_text(geoip.get("country_name")),
        "geo_city": _as_text(geoip.get("city")),
        "chips": chips,
    }


def summarize_blink_account_state(session_data: dict[str, Any], *, fallback_email: str = "") -> dict[str, Any]:
    user = _as_dict(session_data.get("user"))
    workspace = _as_dict(session_data.get("workspace"))
    usage = _as_dict(user.get("usage") or workspace.get("usage"))
    overview = build_blink_account_overview(session_data, fallback_email=fallback_email)

    plan_name = _as_text(overview.get("plan_name") or "unknown")
    billing_limit = _as_int(overview.get("billing_period_credits_limit"))
    daily_limit = _as_int(overview.get("daily_credits_limit"))
    monthly_limit = _as_int(overview.get("monthly_credits_limit"))
    message_parts = [f"Current plan: {plan_name.upper() if plan_name else 'UNKNOWN'}"]
    if billing_limit:
        message_parts.append(f"Billing period quota {billing_limit}")
    elif monthly_limit:
        message_parts.append(f"Monthly quota {monthly_limit}")
    if daily_limit:
        message_parts.append(f"Daily quota {daily_limit}")

    return {
        "valid": bool(user),
        "message": ", ".join(message_parts),
        "remote_user": user,
        "workspace": workspace,
        "usage": usage,
        "tier": _as_text(workspace.get("tier")),
        "workspace_id": _as_text(workspace.get("id")),
        "workspace_slug": _as_text(workspace.get("slug")),
        "customer_id": _as_text(user.get("customer_id") or workspace.get("customer_id")),
        "referral_code": _as_text(workspace.get("referral_code") or user.get("referral_code")),
        "billing_period_credits_limit": billing_limit,
        "daily_credits_limit": daily_limit,
        "monthly_credits_limit": monthly_limit,
        "account_overview": overview,
    }


def extract_blink_account_context(account: Any) -> dict[str, str]:
    extra = _as_dict(getattr(account, "extra", {}) or {})
    overview = _as_dict(extra.get("account_overview"))
    legacy_extra = _as_dict(overview.get("legacy_extra"))
    return {
        "access_token": _as_text(extra.get("access_token")),
        "refresh_token": _as_text(extra.get("refresh_token")),
        "id_token": _as_text(extra.get("id_token")),
        "firebase_refresh_token": _as_text(
            extra.get("firebase_refresh_token")
            or extra.get("legacy_token")
            or getattr(account, "token", "")
        ),
        "session_token": _as_text(
            extra.get("session_token")
            or extra.get("session_cookie")
            or legacy_extra.get("session_token")
            or legacy_extra.get("session_cookie")
        ),
        "workspace_slug": _as_text(
            extra.get("workspace_slug")
            or overview.get("workspace_slug")
            or legacy_extra.get("workspace_slug")
        ),
        "workspace_id": _as_text(extra.get("workspace_id") or overview.get("workspace_id")),
        "customer_id": _as_text(extra.get("customer_id") or overview.get("customer_id")),
        "referral_code": _as_text(extra.get("referral_code") or overview.get("referral_code")),
    }


class BlinkRegister(ManagedSession):
    def __init__(self, proxy: str | None = None):
        self._proxy = proxy
        self._log: Callable[[str], None] = print

    def _create_session(self):
        s = curl_requests.Session()
        s.impersonate = "chrome131"
        if self._proxy:
            s.proxies = {"http": self._proxy, "https": self._proxy}
        s.headers.update(
            {
                "user-agent": UA,
                "accept-language": "zh-CN,zh;q=0.9",
                "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            }
        )
        return s

    @property
    def s(self):
        return self._get_session()

    def log(self, msg: str) -> None:
        self._log(msg)

    def _set_cookie(self, name: str, value: str) -> None:
        text = _as_text(value)
        if not text:
            return
        self.s.cookies.set(name, text, domain="blink.new", path="/")

    def _bind_workspace_slug(self, workspace_slug: str) -> None:
        self._set_cookie("workspace_slug", workspace_slug)

    def _bind_session_token(self, session_token: str) -> None:
        self._set_cookie("session", session_token)

    def _auth_headers(self, *, access_token: str = "", referer: str = "") -> dict[str, str]:
        headers = {
            "accept": "*/*",
            "origin": BLINK_BASE,
            "referer": referer or BLINK_BASE,
        }
        if access_token:
            headers["authorization"] = f"Bearer {access_token}"
        return headers

    def step1_send_magic_link(self, email: str, *, redirect_url: str = "/") -> bool:
        self.log(f"Step1: Sending magic link to {email}")
        response = self.s.post(
            f"{BLINK_BASE}/api/auth/main-app/magic-link",
            json={"email": email, "redirectUrl": redirect_url or "/"},
            headers={
                "accept": "*/*",
                "content-type": "application/json",
                "origin": BLINK_BASE,
                "referer": f"{BLINK_BASE}/sign-up",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
            },
        )
        self.log(f"  -> {response.status_code} {response.text[:200]}")
        if response.status_code != 200:
            raise RuntimeError(f"Magic link send failed: {response.status_code} {response.text[:200]}")
        return bool(response.json().get("success"))

    def step2_redeem_magic_link(self, token: str, email: str) -> dict[str, Any]:
        self.log(f"Step2: Redeeming magic link token={token[:16]}...")
        response = self.s.get(
            f"{BLINK_BASE}/api/auth/main-app/magic-link",
            params={"token": token, "email": email},
            headers={
                "accept": "*/*",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": f"{BLINK_BASE}/auth",
            },
        )
        self.log(f"  -> {response.status_code}")
        if response.status_code != 200:
            raise RuntimeError(f"Magic link redeem failed: {response.status_code} {response.text[:300]}")
        data = response.json()
        if not data.get("success"):
            raise RuntimeError(f"Magic link invalid: {data.get('error', 'Unknown error')}")
        return data

    def step3_firebase_signin(self, custom_token: str) -> dict[str, Any]:
        self.log("Step3: Firebase signInWithCustomToken")
        response = self.s.post(
            FIREBASE_SIGNIN_URL,
            json={"token": custom_token, "returnSecureToken": True},
            headers={
                "accept": "*/*",
                "content-type": "application/json",
                "origin": BLINK_BASE,
                "referer": BLINK_BASE,
                "x-client-version": FIREBASE_CLIENT_VERSION,
                "x-firebase-gmpid": FIREBASE_GMP_ID,
            },
        )
        self.log(f"  -> {response.status_code}")
        if response.status_code != 200:
            raise RuntimeError(f"Firebase signin failed: {response.status_code} {response.text[:300]}")
        return response.json()

    def step3_refresh_firebase(self, firebase_refresh_token: str) -> dict[str, Any]:
        self.log("Step3R: Firebase refresh token")
        response = self.s.post(
            FIREBASE_REFRESH_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": firebase_refresh_token,
            },
            headers={
                "accept": "*/*",
                "content-type": "application/x-www-form-urlencoded",
                "origin": BLINK_BASE,
                "referer": BLINK_BASE,
            },
        )
        self.log(f"  -> {response.status_code}")
        if response.status_code != 200:
            raise RuntimeError(f"Firebase refresh failed: {response.status_code} {response.text[:300]}")
        return response.json()

    def step4_exchange_app_token(self, id_token: str, *, workspace_slug: str = "") -> dict[str, Any]:
        self.log("Step4: Exchanging Blink app token")
        self._bind_workspace_slug(workspace_slug)
        referer = f"{BLINK_BASE}/{workspace_slug}" if workspace_slug else BLINK_BASE
        response = self.s.post(
            f"{BLINK_BASE}/api/auth/token",
            json={"idToken": id_token},
            headers={
                "accept": "*/*",
                "content-type": "application/json",
                "origin": BLINK_BASE,
                "referer": referer,
            },
        )
        self.log(f"  -> {response.status_code}")
        if response.status_code != 200:
            raise RuntimeError(f"Blink token exchange failed: {response.status_code} {response.text[:300]}")
        return response.json()

    def step5_get_session_token(self, id_token: str, *, workspace_slug: str = "") -> str:
        self.log("Step5: Getting session cookie")
        self._bind_workspace_slug(workspace_slug)
        referer = f"{BLINK_BASE}/{workspace_slug}" if workspace_slug else BLINK_BASE
        response = self.s.post(
            f"{BLINK_BASE}/api/auth/session",
            json={"idToken": id_token},
            headers={
                "accept": "*/*",
                "content-type": "application/json",
                "origin": BLINK_BASE,
                "referer": referer,
            },
        )
        self.log(f"  -> {response.status_code}")
        if response.status_code != 200:
            raise RuntimeError(f"Session cookie get failed: {response.status_code} {response.text[:200]}")
        for cookie in self.s.cookies.jar:
            if cookie.name == "session":
                self.log("  session cookie ok")
                return cookie.value
        raise RuntimeError("Blink did not return session cookie")

    def step6_create_user(
        self,
        id_token: str,
        email: str,
        *,
        user_id: str = "",
        workspace_slug: str = "",
        geoip: dict[str, Any] | None = None,
        signup_source: str = "auth_page",
    ) -> dict[str, Any]:
        self.log("Step6: Creating user record")
        self._bind_workspace_slug(workspace_slug)
        username = user_id[-16:] if user_id else ""
        payload: dict[str, Any] = {
            "email": email,
            "name": None,
            "photo_url": None,
            "username": username,
            "email_verified": False,
            "referred_by": None,
            "user_agent": UA,
            "is_same_browser": False,
            "provider_id": None,
            "signup_source": signup_source,
        }
        if geoip:
            payload["geoip"] = dict(geoip)
        referer = f"{BLINK_BASE}/{workspace_slug}" if workspace_slug else BLINK_BASE
        response = self.s.post(
            f"{BLINK_BASE}/api/users/create",
            json=payload,
            headers={
                "accept": "*/*",
                "content-type": "application/json",
                "authorization": f"Bearer {id_token}",
                "origin": BLINK_BASE,
                "referer": referer,
            },
        )
        self.log(f"  -> {response.status_code}")
        if response.status_code != 200:
            raise RuntimeError(f"User record creation failed: {response.status_code} {response.text[:300]}")
        return response.json()

    def step7_post_register(
        self,
        id_token: str,
        *,
        user_id: str,
        workspace_id: str,
        workspace_slug: str = "",
    ) -> dict[str, Any]:
        self.log("Step7: Post-register actions")
        self._bind_workspace_slug(workspace_slug)
        referer = f"{BLINK_BASE}/{workspace_slug}" if workspace_slug else BLINK_BASE
        migrate_response = self.s.post(
            f"{BLINK_BASE}/api/credits/migrate",
            json={"userId": user_id},
            headers={
                "authorization": f"Bearer {id_token}",
                "content-type": "application/json",
                "origin": BLINK_BASE,
                "referer": referer,
            },
        )
        referral_payload: dict[str, Any] = {}
        if workspace_id:
            referral_response = self.s.post(
                f"{BLINK_BASE}/api/referral/generate",
                json={"workspace_id": workspace_id},
                headers={
                    "authorization": f"Bearer {id_token}",
                    "content-type": "application/json",
                    "origin": BLINK_BASE,
                    "referer": referer,
                },
            )
            if referral_response.status_code == 200:
                referral_payload = _as_dict(referral_response.json())
        self.log(
            f"  migrate -> {migrate_response.status_code}"
            + (f", referral -> {referral_response.status_code}" if workspace_id else "")
        )
        return {
            "migrate_ok": migrate_response.status_code == 200,
            "referral_code": _as_text(referral_payload.get("referral_code")),
        }

    def fetch_session_data(
        self,
        id_token: str,
        *,
        session_token: str = "",
        workspace_slug: str = "",
        referer: str = "",
    ) -> dict[str, Any]:
        self._bind_workspace_slug(workspace_slug)
        self._bind_session_token(session_token)
        target_referer = referer or (f"{BLINK_BASE}/{workspace_slug}" if workspace_slug else BLINK_BASE)
        response = self.s.get(
            f"{BLINK_BASE}/api/auth/session-data",
            headers=self._auth_headers(access_token=id_token, referer=target_referer),
        )
        if response.status_code != 200:
            raise RuntimeError(f"Blink account state fetch failed: {response.status_code} {response.text[:300]}")
        return response.json()

    def create_checkout(
        self,
        id_token: str,
        *,
        price_id: str,
        plan_id: str,
        workspace_id: str,
        cancel_url: str,
        session_token: str = "",
        workspace_slug: str = "",
        tolt_referral_id: str | None = None,
    ) -> dict[str, Any]:
        self._bind_workspace_slug(workspace_slug)
        self._bind_session_token(session_token)
        referer = cancel_url or (f"{BLINK_BASE}/{workspace_slug}?showPricing=true" if workspace_slug else BLINK_BASE)
        response = self.s.post(
            f"{BLINK_BASE}/api/stripe/checkout",
            json={
                "priceId": price_id,
                "planId": plan_id,
                "toltReferralId": tolt_referral_id,
                "workspaceId": workspace_id,
                "cancelUrl": cancel_url,
            },
            headers={
                **self._auth_headers(access_token=id_token, referer=referer),
                "content-type": "application/json",
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"Blink payment link creation failed: {response.status_code} {response.text[:300]}")
        return response.json()

    def create_api_key(
        self,
        id_token: str,
        *,
        workspace_id: str,
        name: str,
        session_token: str = "",
        workspace_slug: str = "",
    ) -> dict[str, Any]:
        self._bind_workspace_slug(workspace_slug)
        self._bind_session_token(session_token)
        referer = f"{BLINK_BASE}/settings?tab=api-keys"
        response = self.s.post(
            f"{BLINK_BASE}/api/workspace/api-keys",
            json={
                "workspaceId": workspace_id,
                "name": name,
            },
            headers={
                **self._auth_headers(access_token=id_token, referer=referer),
                "content-type": "application/json",
            },
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Blink API Key creation failed: {response.status_code} {response.text[:300]}")
        return response.json()

    def refresh_auth_session(self, firebase_refresh_token: str, *, workspace_slug: str = "") -> dict[str, str]:
        firebase_data = self.step3_refresh_firebase(firebase_refresh_token)
        id_token = _as_text(firebase_data.get("id_token") or firebase_data.get("access_token"))
        next_firebase_refresh_token = _as_text(firebase_data.get("refresh_token") or firebase_refresh_token)
        if not id_token:
            raise RuntimeError("Firebase refresh did not return id_token")

        app_tokens = self.step4_exchange_app_token(id_token, workspace_slug=workspace_slug)
        access_token = _as_text(app_tokens.get("access_token"))
        refresh_token = _as_text(app_tokens.get("refresh_token"))
        session_token = self.step5_get_session_token(id_token, workspace_slug=workspace_slug)
        if not access_token:
            raise RuntimeError("Blink token refresh did not return access_token")
        return {
            "id_token": id_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "firebase_refresh_token": next_firebase_refresh_token,
            "session_token": session_token,
        }


def load_blink_account_state(
    account: Any,
    *,
    proxy: str | None = None,
    log_fn: Callable[[str], None] = print,
    force_refresh: bool = False,
) -> dict[str, Any]:
    context = extract_blink_account_context(account)
    client = BlinkRegister(proxy=proxy)
    client._log = log_fn

    id_token = context["id_token"]
    session_token = context["session_token"]
    workspace_slug = context["workspace_slug"]
    fallback_email = _as_text(getattr(account, "email", ""))

    session_data: dict[str, Any] | None = None
    if id_token and not force_refresh:
        try:
            session_data = client.fetch_session_data(
                id_token,
                session_token=session_token,
                workspace_slug=workspace_slug,
            )
        except Exception as exc:
            client.log(f"Existing Blink id_token unavailable, attempting refresh: {exc}")

    if session_data is None:
        firebase_refresh_token = context["firebase_refresh_token"]
        if not firebase_refresh_token:
            raise RuntimeError("Account missing firebase_refresh_token, cannot refresh Blink session")
        refreshed = client.refresh_auth_session(firebase_refresh_token, workspace_slug=workspace_slug)
        context.update(refreshed)
        session_data = client.fetch_session_data(
            context["id_token"],
            session_token=context["session_token"],
            workspace_slug=workspace_slug,
        )

    summary = summarize_blink_account_state(session_data, fallback_email=fallback_email)
    return {
        **context,
        "session_data": session_data,
        "account_overview": summary["account_overview"],
        "summary": summary,
    }
