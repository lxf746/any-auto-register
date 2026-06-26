"""Cloudflare Worker self-hosted temporary mailbox provider."""
import logging
import re
import time

import requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link

logger = logging.getLogger(__name__)


class CFWorkerMailbox(BaseMailbox):
    """Cloudflare Worker self-hosted temporary mailbox service"""

    @classmethod
    def from_config(cls, config: dict) -> 'CFWorkerMailbox':
        return cls(
            api_url=config.get("cfworker_api_url", ""),
            admin_token=config.get("cfworker_admin_token", ""),
            domain=config.get("cfworker_domain", ""),
            fingerprint=config.get("cfworker_fingerprint", ""),
            proxy=config.get("proxy"),
        )

    def __init__(self, api_url: str, admin_token: str = "", domain: str = "",
                 fingerprint: str = "", proxy: str = None):
        self.api = api_url.rstrip("/")
        self.admin_token = admin_token
        self.domain = domain
        self.fingerprint = fingerprint
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._token = None

    def _headers(self) -> dict:
        h = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "x-admin-auth": self.admin_token,
        }
        if self.fingerprint:
            h["x-fingerprint"] = self.fingerprint
        return h

    def get_email(self) -> MailboxAccount:
        import random, string
        name = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        payload = {"enablePrefix": True, "name": name}
        if self.domain:
            payload["domain"] = self.domain
        r = requests.post(f"{self.api}/admin/new_address",
            json=payload, headers=self._headers(),
            proxies=self.proxy, timeout=15)
        logger.debug("new_address status=%d resp=%s", r.status_code, r.text[:200])
        data = r.json()
        email = data.get("email", data.get("address", ""))
        token = data.get("token", data.get("jwt", ""))
        self._token = token
        logger.info("Generated mailbox: %s token=%s...", email, token[:40] if token else 'NONE')
        return MailboxAccount(
            email=email,
            account_id=token,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "cfworker",
                    "resource_type": "mailbox",
                    "resource_identifier": token or email,
                    "handle": email,
                    "display_name": email,
                    "metadata": {
                        "email": email,
                        "token": token,
                        "api_url": self.api,
                        "domain": self.domain,
                    },
                },
            },
        )

    def _get_mails(self, email: str) -> list:
        r = requests.get(f"{self.api}/admin/mails",
            params={"limit": 20, "offset": 0, "address": email},
            headers=self._headers(), proxies=self.proxy, timeout=10)
        data = r.json()
        return data.get("results", data) if isinstance(data, dict) else data

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            mails = self._get_mails(account.email)
            return {str(m.get("id", "")) for m in mails}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                mails = self._get_mails(account.email)
                for mail in sorted(mails, key=lambda x: x.get("id", 0), reverse=True):
                    mid = str(mail.get("id", ""))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    raw = str(mail.get("raw", ""))
                    # 1. Prefer matching <span>XXXXXX</span> (Trae email format)
                    code_m = re.search(r'<span[^>]*>\s*(\d{6})\s*</span>', raw)
                    if code_m:
                        return code_m.group(1)
                    # 2. Skip MIME header, search only body part to avoid matching timestamps
                    body_start = raw.find('\r\n\r\n')
                    search_text = raw[body_start:] if body_start != -1 else raw
                    search_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', search_text)
                    # Exclude timestamp patterns m=+XXXXXX. and t=XXXXXXXXXX
                    search_text = re.sub(r'm=\+\d+\.\d+', '', search_text)
                    search_text = re.sub(r'\bt=\d+\b', '', search_text)
                    m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', search_text)
                    if m:
                        return m.group(1) if m.groups() else m.group(0)
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
                mails = self._get_mails(account.email)
                for mail in sorted(mails, key=lambda x: x.get("id", 0), reverse=True):
                    mid = str(mail.get("id", ""))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    raw = str(mail.get("raw", ""))
                    link = extract_verification_link(raw, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")
