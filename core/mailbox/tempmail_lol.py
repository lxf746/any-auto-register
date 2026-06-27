"""tempmail.lol free temporary mailbox provider."""
import logging
import re
import time

import requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link

logger = logging.getLogger(__name__)

DEFAULT_TEMPMAIL_LOL_API_URL = "https://api.tempmail.lol/v2"


class TempMailLolMailbox(BaseMailbox):
    """tempmail.lol free temporary mailbox (auto-generated, no registration required)"""

    @classmethod
    def from_config(cls, config: dict) -> 'TempMailLolMailbox':
        from core.mailbox.config import TempMailLolConfig
        cfg = TempMailLolConfig(
            api_url=config.get("tempmail_lol_api_url", ""),
            proxy=config.get("proxy"),
        )
        return cls(
            api_url=cfg.api_url,
            proxy=cfg.proxy,
        )

    def __init__(self, proxy: str = None, api_url: str = ""):
        self.api = (api_url or DEFAULT_TEMPMAIL_LOL_API_URL).rstrip("/")
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._token = None
        self._email = None

    def get_email(self) -> MailboxAccount:
        r = requests.post(f"{self.api}/inbox/create",
            json={},
            proxies=self.proxy, timeout=15)
        if r.status_code not in (200, 201):
            error_text = r.text[:300]
            try:
                error_detail = r.json()
            except Exception:
                error_detail = None
            raise RuntimeError(
                f"tempmail.lol create inbox failed: HTTP {r.status_code} {error_text}"
            )
        data = r.json()
        self._email = data.get("address") or data.get("email", "")
        self._token = data.get("token", "")
        if not self._email:
            raise RuntimeError(f"tempmail.lol create inbox returned empty email: {data}")
        return MailboxAccount(
            email=self._email,
            account_id=self._token,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "tempmail_lol",
                    "resource_type": "mailbox",
                    "resource_identifier": self._token,
                    "handle": self._email,
                    "display_name": self._email,
                    "metadata": {
                        "email": self._email,
                        "token": self._token,
                    },
                },
            },
        )

    def _get_mailtm_token(self, account: MailboxAccount) -> str:
        """Extract mail.tm Bearer token from account extra metadata."""
        return (account.extra or {}).get("provider_resource", {}).get("metadata", {}).get("token", "")

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            token = self._get_mailtm_token(account)
            if not token:
                return set()
            r = requests.get(f"{self.api}/messages",
                headers={"Authorization": f"Bearer {token}"},
                proxies=self.proxy, timeout=10)
            if r.status_code != 200:
                return set()
            return {str(m["id"]) for m in r.json().get("hydra:member", [])}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        token = self._get_mailtm_token(account)
        if not token:
            raise RuntimeError("mail.tm: missing token in account metadata")
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.api}/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    proxies=self.proxy, timeout=10)
                if r.status_code != 200:
                    raise RuntimeError(f"mail.tm messages fetch failed: HTTP {r.status_code}")
                messages = r.json().get("hydra:member", [])
                for mail in sorted(messages, key=lambda x: x.get("createdAt", ""), reverse=True):
                    mid = str(mail.get("id", ""))
                    if mid in seen:
                        continue
                    seen.add(mid)
                    # Fetch full message
                    msg_r = requests.get(f"{self.api}/messages/{mid}",
                        headers={"Authorization": f"Bearer {token}"},
                        proxies=self.proxy, timeout=10)
                    msg = msg_r.json()
                    text = str(msg.get("subject", "")) + " " + str(msg.get("text", "")) + " " + str(msg.get("html", ""))
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    m = re.search(code_pattern or r'(?<!#)(?<!<\d)(<\d{6})(?!<\d)', text)
                    if m:
                        return m.group(1) if m.groups() else m.group(0)
            except Exception as e:
                logger.error("[mail.tm wait_for_code] Error: %s", e)
            time.sleep(3)
        raise TimeoutError(f"Verification code wait timed out ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        token = self._get_mailtm_token(account)
        if not token:
            raise RuntimeError("mail.tm: missing token in account metadata")
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.api}/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    proxies=self.proxy, timeout=10)
                if r.status_code != 200:
                    raise RuntimeError(f"mail.tm messages fetch failed: HTTP {r.status_code}")
                for mail in sorted(r.json().get("hydra:member", []), key=lambda x: x.get("createdAt", ""), reverse=True):
                    mid = str(mail.get("id", ""))
                    if mid in seen:
                        continue
                    seen.add(mid)
                    msg_r = requests.get(f"{self.api}/messages/{mid}",
                        headers={"Authorization": f"Bearer {token}"},
                        proxies=self.proxy, timeout=10)
                    msg = msg_r.json()
                    text = str(msg.get("subject", "")) + " " + str(msg.get("text", "")) + " " + str(msg.get("html", ""))
                    link = extract_verification_link(text, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")
