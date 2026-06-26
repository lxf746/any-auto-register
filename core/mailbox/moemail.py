"""MoeMail (sall.cc) mailbox provider."""
import logging
import random
import re
import string
import time
from urllib.parse import urlencode, urlparse

import requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link, normalize_api_base_url
from core.tls import mark_session_insecure, suppress_insecure_request_warning

logger = logging.getLogger(__name__)


class MoeMailMailbox(BaseMailbox):
    """MoeMail (sall.cc) mailbox service - auto-register account and generate temporary mailbox"""

    def __init__(
        self,
        api_url: str = "",
        username: str = "",
        password: str = "",
        session_token: str = "",
        proxy: str = None,
    ):
        self.api = normalize_api_base_url(api_url, default="", label="MoeMail API URL")
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._configured_username = str(username or "").strip()
        self._configured_password = str(password or "")
        self._configured_session_token = str(session_token or "").strip()
        self._session_token = self._configured_session_token or None
        self._email = None
        self._session = None
        self._username = self._configured_username
        self._password = self._configured_password

    def _new_session(self):
        s = requests.Session()
        s.proxies = self.proxy
        mark_session_insecure(s)
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        s.headers.update({"user-agent": ua, "origin": self.api, "referer": f"{self.api}/zh-CN/login"})
        return s

    def _extract_session_token(self, session) -> str:
        for cookie in session.cookies:
            if "session-token" in cookie.name:
                return cookie.value
        return ""

    def _apply_session_token(self, session, token: str) -> None:
        domain = urlparse(self.api).hostname or ""
        cookie_names = [
            "__Secure-authjs.session-token",
            "authjs.session-token",
            "__Secure-next-auth.session-token",
            "next-auth.session-token",
        ]
        for name in cookie_names:
            session.cookies.set(name, token, domain=domain, path="/")
            session.cookies.set(name, token, path="/")

    def _login_with_existing_account(self) -> str:
        s = self._new_session()

        if self._configured_session_token:
            self._apply_session_token(s, self._configured_session_token)
            self._session = s
            self._session_token = self._configured_session_token
            logger.info("Using provided session-token")
            return self._configured_session_token

        if not (self._configured_username and self._configured_password):
            raise RuntimeError("MoeMail no reusable account configured, please provide username/password or session-token")

        with suppress_insecure_request_warning():
            csrf_r = s.get(f"{self.api}/api/auth/csrf", timeout=10)
        csrf = csrf_r.json().get("csrfToken", "")
        with suppress_insecure_request_warning():
            login_resp = s.post(
                f"{self.api}/api/auth/callback/credentials",
                headers={"content-type": "application/x-www-form-urlencoded"},
                data=urlencode({
                    "username": self._configured_username,
                    "password": self._configured_password,
                    "csrfToken": csrf,
                    "redirect": "false",
                    "callbackUrl": self.api,
                }),
                allow_redirects=True,
                timeout=15,
            )
        self._session = s
        self._username = self._configured_username
        self._password = self._configured_password
        token = self._extract_session_token(s)
        if token:
            self._session_token = token
            logger.info("Successfully logged in with manually registered account")
            return token
        raise RuntimeError(
            f"MoeMail login failed: username/password provided but session-token not obtained (HTTP {login_resp.status_code})"
        )

    def _ensure_session(self) -> str:
        if self._session_token and self._session is not None:
            return self._session_token
        if self._configured_session_token or self._configured_username:
            return self._login_with_existing_account()
        return self._register_and_login()

    def _register_and_login(self) -> str:
        s = self._new_session()
        # Register
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        password = "Test" + "".join(random.choices(string.digits, k=8)) + "!"
        self._username = username
        self._password = password
        logger.info("Registering account: %s / %s", username, password)
        with suppress_insecure_request_warning():
            r_reg = s.post(f"{self.api}/api/auth/register",
                json={"username": username, "password": password, "turnstileToken": ""},
                timeout=15)
        logger.info("Register result: %d %s", r_reg.status_code, r_reg.text[:80])
        if r_reg.status_code >= 400:
            try:
                register_error = r_reg.json().get("error") or r_reg.text
            except Exception:
                register_error = r_reg.text
            raise RuntimeError(f"MoeMail registration failed: {str(register_error).strip() or f'HTTP {r_reg.status_code}'}")
        # Get CSRF
        with suppress_insecure_request_warning():
            csrf_r = s.get(f"{self.api}/api/auth/csrf", timeout=10)
        csrf = csrf_r.json().get("csrfToken", "")
        # Login
        with suppress_insecure_request_warning():
            login_resp = s.post(f"{self.api}/api/auth/callback/credentials",
                headers={"content-type": "application/x-www-form-urlencoded"},
                data=urlencode({
                    "username": username,
                    "password": password,
                    "csrfToken": csrf,
                    "redirect": "false",
                    "callbackUrl": self.api,
                }),
                allow_redirects=True, timeout=15)
        self._session = s
        token = self._extract_session_token(s)
        if token:
            self._session_token = token
            logger.info("Login successful")
            return token
        logger.warning("Login failed, cookies: %s", [c.name for c in s.cookies])
        raise RuntimeError(
            f"MoeMail login failed: session-token not obtained (HTTP {login_resp.status_code})"
        )

    # Prefer these domains (better reputation, less likely to be rejected by AWS/Google)
    _PREFERRED_DOMAINS = ("sall.cc", "cnmlgb.de", "zhooo.org", "coolkid.icu")

    def get_email(self) -> MailboxAccount:
        self._session_token = self._configured_session_token or None
        self._session = None
        self._ensure_session()
        name = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        # Fetch available domain list, prefer reputable domains to avoid rejection by AWS and other platforms
        domain = "sall.cc"
        try:
            with suppress_insecure_request_warning():
                cfg_r = self._session.get(f"{self.api}/api/config", timeout=10)
            all_domains = [d.strip() for d in cfg_r.json().get("emailDomains", "sall.cc").split(",") if d.strip()]
            if all_domains:
                # Filter preferred domains from available ones, selecting in _PREFERRED_DOMAINS order
                preferred = [d for d in self._PREFERRED_DOMAINS if d in all_domains]
                if preferred:
                    domain = random.choice(preferred)
                else:
                    # No preferred domains available, randomly select from remaining
                    domain = random.choice(all_domains)
        except Exception:
            pass
        with suppress_insecure_request_warning():
            r = self._session.post(f"{self.api}/api/emails/generate",
                json={"name": name, "domain": domain, "expiryTime": 86400000},
                timeout=15)
        data = r.json()
        self._email = data.get("email", data.get("address", ""))
        email_id = data.get("id", "")
        logger.info("Generated mailbox: %s id=%s domain=%s status=%d", self._email, email_id, domain, r.status_code)
        if not email_id:
            logger.warning("Generation failed: %s", data)
            generate_error = data.get("error") or data.get("message") or r.text
            raise RuntimeError(f"MoeMail mailbox generation failed: {str(generate_error).strip() or f'HTTP {r.status_code}'}")
        if not self._email:
            raise RuntimeError("MoeMail mailbox generation failed: response missing email")
        self._email_count = getattr(self, '_email_count', 0) + 1
        return MailboxAccount(
            email=self._email,
            account_id=str(email_id),
            extra={
                "provider_account": {
                    "provider_type": "mailbox",
                    "provider_name": "moemail",
                    "login_identifier": getattr(self, "_username", ""),
                    "display_name": getattr(self, "_username", "") or self._email,
                    "credentials": {
                        "username": getattr(self, "_username", ""),
                        "password": getattr(self, "_password", ""),
                        "session_token": self._session_token,
                    },
                    "metadata": {
                        "api_url": self.api,
                        "email": self._email,
                    },
                },
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "moemail",
                    "resource_type": "mailbox",
                    "resource_identifier": str(email_id),
                    "handle": self._email,
                    "display_name": self._email,
                    "metadata": {
                        "email": self._email,
                        "api_url": self.api,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            with suppress_insecure_request_warning():
                r = self._session.get(f"{self.api}/api/emails/{account.account_id}", timeout=10)
            return {str(m.get("id", "")) for m in r.json().get("messages", [])}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None,
                      code_pattern: str = None) -> str:
        seen = set(before_ids or [])
        start = time.time()
        pattern = re.compile(code_pattern) if code_pattern else None
        while time.time() - start < timeout:
            try:
                with suppress_insecure_request_warning():
                    r = self._session.get(f"{self.api}/api/emails/{account.account_id}",
                        timeout=10)
                msgs = r.json().get("messages", [])
                for msg in msgs:
                    mid = str(msg.get("id", ""))
                    if not mid or mid in seen: continue
                    seen.add(mid)
                    body = str(msg.get("content") or msg.get("text") or msg.get("body") or msg.get("html") or "") + " " + str(msg.get("subject") or "")
                    body = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', body)
                    if pattern:
                        m = pattern.search(body)
                    else:
                        m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', body)
                    if m: return m.group(1) if m.groups() else m.group(0) if code_pattern else m.group(1)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification code wait timed out ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                with suppress_insecure_request_warning():
                    r = self._session.get(f"{self.api}/api/emails/{account.account_id}",
                        timeout=10)
                msgs = r.json().get("messages", [])
                for msg in msgs:
                    mid = str(msg.get("id", ""))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    body = (
                        str(msg.get("content") or "") + " " +
                        str(msg.get("text") or "") + " " +
                        str(msg.get("body") or "") + " " +
                        str(msg.get("html") or "") + " " +
                        str(msg.get("subject") or "")
                    )
                    link = extract_verification_link(body, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")
