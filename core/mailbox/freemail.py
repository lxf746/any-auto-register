"""Freemail self-hosted email service provider."""
import logging
import re
import time

import requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link

logger = logging.getLogger(__name__)


class FreemailMailbox(BaseMailbox):
    """
    Freemail self-hosted email service (based on Cloudflare Worker)
    Project: https://github.com/idinging/freemail
    Supports admin token and username/password authentication
    """

    def __init__(self, api_url: str, admin_token: str = "",
                 username: str = "", password: str = "",
                 proxy: str = None):
        self.api = api_url.rstrip("/")
        self.admin_token = admin_token
        self.username = username
        self.password = password
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._session = None
        self._email = None

    def _get_session(self):
        s = requests.Session()
        s.proxies = self.proxy
        if self.admin_token:
            s.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        elif self.username and self.password:
            s.post(f"{self.api}/api/login",
                json={"username": self.username, "password": self.password},
                timeout=15)
        self._session = s
        return s

    def get_email(self) -> MailboxAccount:
        if not self._session:
            self._get_session()
        r = self._session.get(f"{self.api}/api/generate", timeout=15)
        data = r.json()
        email = data.get("email", "")
        self._email = email
        logger.info("Generated mailbox: %s", email)
        provider_account = {
            "provider_type": "mailbox",
            "provider_name": "freemail",
            "login_identifier": self.username or email,
            "display_name": self.username or email,
            "credentials": {},
            "metadata": {
                "api_url": self.api,
                "auth_mode": "admin_token" if self.admin_token else "username_password",
            },
        }
        if self.admin_token:
            provider_account["credentials"]["admin_token"] = self.admin_token
        if self.username:
            provider_account["credentials"]["username"] = self.username
        if self.password:
            provider_account["credentials"]["password"] = self.password
        return MailboxAccount(
            email=email,
            account_id=email,
            extra={
                "provider_account": provider_account,
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "freemail",
                    "resource_type": "mailbox",
                    "resource_identifier": email,
                    "handle": email,
                    "display_name": email,
                    "metadata": {
                        "email": email,
                        "api_url": self.api,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            r = self._session.get(f"{self.api}/api/emails",
                params={"mailbox": account.email, "limit": 50}, timeout=10)
            return {str(m["id"]) for m in r.json() if "id" in m}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = self._session.get(f"{self.api}/api/emails",
                    params={"mailbox": account.email, "limit": 20}, timeout=10)
                for msg in r.json():
                    mid = str(msg.get("id", ""))
                    if not mid or mid in seen: continue
                    seen.add(mid)
                    # Use verification_code field directly
                    code = str(msg.get("verification_code") or "")
                    if code and code != "None":
                        return code
                    # Fallback: extract from preview
                    text = str(msg.get("preview", "")) + " " + str(msg.get("subject", ""))
                    m = re.search(r"(?<!\d)(\d{6})(?!\d)", text)
                    if m: return m.group(1)
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
                r = self._session.get(f"{self.api}/api/emails",
                    params={"mailbox": account.email, "limit": 20}, timeout=10)
                for msg in r.json():
                    mid = str(msg.get("id", ""))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = " ".join(
                        str(msg.get(key, ""))
                        for key in ("preview", "subject", "html", "text", "content", "body")
                    )
                    link = extract_verification_link(text, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")
