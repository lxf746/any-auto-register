"""kimchi.dev protocol registration core implementation.

Proven working flow:
  1. POST /dbconnections/signup (via proxy) → create Auth0 account
  2. Poll tempmail.lol for verification email
  3. Follow SendGrid tracking URL → get Auth0 email-verification ticket URL
  4. Browser: goto ticket URL → auto-verifies email → redirects to login page
  5. Browser: fill login form (#login-email, #login-password) → click "Sign in"
  6. Browser: extract cast-console-auth cookie after redirect
  7. Use cookie to POST /v1/auth/tokens → create Cast.ai API key
  8. Validate API key against llm.kimchi.dev
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Optional

from curl_cffi import requests as curl_requests
import requests as std_requests

KIMCHI_CAST_API = "https://api.cast.ai"
KIMCHI_LLM_BASE = "https://llm.kimchi.dev"

AUTH0_DOMAIN = "login.cast.ai"
AUTH0_CLIENT_ID = "C3wJOaBvdIGIcSpdHhLeiN6sIVA1iDhK"
AUTH0_REDIRECT_URI = "https://console.cast.ai/api/auth"
AUTH0_DB_CONNECTION = "Username-Password-Authentication"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)

PROXY_URL = (
    "https://api.proxyscrape.com/v4/free-proxy-list/get"
    "?request=display_proxies&proxy_format=protocolipport"
    "&format=text&protocol=http&timeout=5000"
)

TEMPMAIL_API = "https://api.tempmail.lol/v2"


class KimchiAuthError(Exception):
    def __init__(self, message: str, code: str = "", status_code: int = 0, raw: Any = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.raw = raw


class KimchiRateLimitError(KimchiAuthError):
    pass


class KimchiEmailVerificationRequired(Exception):
    def __init__(self, message: str = "Email verification required", verification_url: str = ""):
        super().__init__(message)
        self.verification_url = verification_url


def _fresh_session(proxy: str | None = None) -> curl_requests.Session:
    s = curl_requests.Session()
    s.impersonate = "chrome131"
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    s.headers.update({
        "user-agent": UA,
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
    })
    return s


def _fetch_proxies(max_proxies: int = 50) -> list[str]:
    try:
        r = std_requests.get(PROXY_URL, timeout=10)
        lines = r.text.strip().split("\n")
        return [p.strip() for p in lines if p.strip()][:max_proxies]
    except Exception:
        return []


class KimchiRegister:
    def __init__(self, proxy: str | None = None, log_fn: Callable[[str], None] = print):
        self._proxy = proxy
        self._log = log_fn
        self._cast_api_key = ""
        self.s = _fresh_session(proxy)

    def log(self, msg: str) -> None:
        self._log(msg)

    def _cast_headers(self, cookie: str = "", **extra: str) -> dict[str, str]:
        h = {"accept": "application/json", "content-type": "application/json"}
        if cookie:
            h["authorization"] = f"Bearer {cookie}"
        elif self._cast_api_key:
            h["authorization"] = f"Bearer {self._cast_api_key}"
        h.update(extra)
        return h

    def _raise_auth_error(self, r, context: str) -> None:
        status = r.status_code
        try:
            data = r.json()
            code = data.get("code") or data.get("error", "")
            desc = data.get("description") or data.get("error_description") or data.get("message") or ""
        except Exception:
            code = ""
            desc = r.text[:300]
        if status == 429 or code in ("too_many_requests", "too_many_attempts", "too_many_signups"):
            raise KimchiRateLimitError(f"{context}: rate limited", code=code, status_code=status, raw=desc)
        raise KimchiAuthError(f"{context}: {desc or f'HTTP {status}'}", code=code, status_code=status, raw=desc)

    # ── Step 1: Signup via proxy ──

    def auth0_signup(self, email: str, password: str, *, max_retries: int = 3) -> dict[str, Any]:
        proxies = _fetch_proxies() if not self._proxy else [self._proxy]
        last_error = None
        for attempt in range(max_retries):
            for i, px in enumerate(proxies[:40]):
                try:
                    s = _fresh_session(px)
                    r = s.post(
                        f"https://{AUTH0_DOMAIN}/dbconnections/signup",
                        json={"client_id": AUTH0_CLIENT_ID, "email": email, "password": password, "connection": AUTH0_DB_CONNECTION},
                        headers={"content-type": "application/json"},
                        timeout=15,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        self.log(f"  Signup OK via proxy #{i+1}")
                        return data
                    if r.status_code == 429:
                        continue
                except Exception:
                    continue
            last_error = KimchiRateLimitError(f"Signup rate limited (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                self.log(f"  Signup: all proxies failed, retrying...")
                time.sleep(10)
        raise last_error or KimchiAuthError("Signup failed: all proxies exhausted")

    # ── Step 2: Poll tempmail.lol for verification email ──

    def wait_for_verification_email(self, token: str, *, timeout: int = 120, poll_interval: int = 5) -> str | None:
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = std_requests.get(f"{TEMPMAIL_API}/inbox", params={"token": token}, timeout=10)
                if r.status_code == 200:
                    msgs = r.json().get("emails") or []
                    if msgs:
                        body = str(msgs[0].get("body", "")) + str(msgs[0].get("html", ""))
                        urls = re.findall(r'https?://[^\s<>"\']+', body)
                        for u in urls:
                            if "sendgrid.net/ls/click" in u:
                                r_track = std_requests.get(u, timeout=15, allow_redirects=False)
                                loc = r_track.headers.get("location", "")
                                if "email-verification" in loc and "ticket=" in loc:
                                    return loc
            except Exception:
                pass
            time.sleep(poll_interval)
        return None

    # ── Step 3: Browser flow ──

    def browser_verify_and_login(self, ticket_url: str, email: str, password: str, *, headless: bool = True, timeout: int = 60) -> str | None:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()

            page.goto(ticket_url, wait_until="networkidle", timeout=timeout * 1000)
            time.sleep(2)
            current = page.url
            self.log(f"  Browser: {current[:80]}...")

            if "login" in current.lower() and "login?" in current:
                try:
                    page.click("button:has-text('Accept all')", timeout=3000)
                    time.sleep(1)
                except Exception:
                    pass

                page.fill("#login-email", email)
                page.fill("#login-password", password)
                self.log("  Filled login form")

                try:
                    page.click("button[type='submit']:has-text('Sign in')", timeout=5000)
                except Exception:
                    page.click("button[type='submit']", timeout=5000)
                self.log("  Clicked Sign in")

                time.sleep(15)

            cookie = None
            for c in page.context.cookies():
                if c["name"] == "cast-console-auth" and "console.cast.ai" in c.get("domain", ""):
                    cookie = c["value"]
                    break

            browser.close()
            return cookie

    # ── Step 4: Create API key ──

    def create_api_key(self, cookie: str, name: str = "auto-register") -> str:
        s = _fresh_session()
        r = s.post(
            f"{KIMCHI_CAST_API}/v1/auth/tokens",
            headers=self._cast_headers(cookie=cookie),
            json={"name": name},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            raise KimchiAuthError(f"API key creation failed: HTTP {r.status_code}", status_code=r.status_code)
        data = r.json()
        key = data.get("token") or data.get("key") or data.get("apiKey") or data.get("api_key") or ""
        if not key:
            raise KimchiAuthError(f"No key in response: {json.dumps(data)[:300]}")
        self.log(f"  Key created: {key[:20]}...")
        return key

    # ── Step 5: Validate ──

    def check_api_key_valid(self, api_key: str) -> dict[str, Any]:
        try:
            r = curl_requests.get(
                f"{KIMCHI_LLM_BASE}/openai/v1/models",
                headers={"authorization": f"Bearer {api_key}", "accept": "application/json"},
                impersonate="chrome131", timeout=15,
            )
            if r.status_code == 200:
                models = [m.get("id", "") for m in r.json().get("data", []) if m.get("id")]
                self.log(f"  Valid, {len(models)} models")
                return {"valid": True, "models": models}
            return {"valid": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    # ── Full registration flow ──

    def register(
        self,
        email: str,
        password: str,
        *,
        api_key_name: str = "auto-register",
        verify_link_callback: Callable[[], str] | None = None,
        mailbox_token: str = "",
        mailbox_create_fn: Callable[[], tuple[str, str]] | None = None,
        headless: bool = True,
        max_verify_wait: int = 120,
    ) -> dict[str, Any]:
        self.log("=== Kimchi.dev registration ===")

        # 1. Signup
        self.log("\n[1/4] Signup...")
        self.auth0_signup(email, password)

        # 2. Wait for verification email
        self.log("\n[2/4] Waiting for verification email...")
        if mailbox_create_fn:
            email, mailbox_token = mailbox_create_fn()
        elif not mailbox_token:
            raise KimchiAuthError("No mailbox_token or mailbox_create_fn provided")

        verify_url = self.wait_for_verification_email(mailbox_token, timeout=max_verify_wait)
        if not verify_url:
            raise KimchiAuthError("Verification email not received")
        self.log(f"  Verification ticket URL: {verify_url[:80]}...")

        # 3. Browser verify + login → get console cookie
        self.log("\n[3/4] Browser verify + login...")
        cookie = self.browser_verify_and_login(verify_url, email, password, headless=headless)
        if not cookie:
            raise KimchiAuthError("Browser login failed: no cast-console-auth cookie")
        self.log(f"  Got console cookie")

        # 4. Create API key
        self.log("\n[4/4] Create API key...")
        api_key = self.create_api_key(cookie, name=api_key_name)

        # 5. Validate
        validation = self.check_api_key_valid(api_key)

        return {
            "email": email,
            "password": password,
            "api_key": api_key,
            "user_id": "",
            "access_token": "",
            "id_token": "",
            "refresh_token": "",
            "validation": validation,
        }

    def import_cast_api_key(self, api_key: str) -> None:
        self._cast_api_key = api_key

    def run_from_cast_api_key(self, cast_api_key: str) -> dict[str, Any]:
        self.log("=== Import Cast.ai API key ===")
        self.import_cast_api_key(cast_api_key)
        validation = self.check_api_key_valid(cast_api_key)
        return {"email": "", "password": "", "api_key": cast_api_key, "user_id": "", "session_token": "", "validation": validation}
