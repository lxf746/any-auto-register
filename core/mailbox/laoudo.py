"""Laoudo.com mailbox provider."""
import re
import time

from curl_cffi import requests as curl_requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link

DEFAULT_LAOUDO_API_URL = "https://laoudo.com/api/email"


class LaoudoMailbox(BaseMailbox):
    """laoudo.com mailbox service"""
    @classmethod
    def from_config(cls, config: dict) -> 'LaoudoMailbox':
        from core.mailbox.config import LaoudoConfig
        cfg = LaoudoConfig(
            auth_token=config.get("laoudo_auth", ""),
            email=config.get("laoudo_email", ""),
            account_id=config.get("laoudo_account_id", ""),
        )
        return cls(
            auth_token=cfg.auth_token,
            email=cfg.email,
            account_id=cfg.account_id,
            api_url=cfg.api_url,
        )

    def __init__(self, auth_token: str, email: str, account_id: str, api_url: str = ""):
        self.auth = auth_token
        self._email = email
        self._account_id = account_id
        self.api = (api_url or DEFAULT_LAOUDO_API_URL).rstrip("/")
        self._ua = "Mozilla/5.0"

    def get_email(self) -> MailboxAccount:
        return MailboxAccount(
            email=self._email,
            account_id=self._account_id,
            extra={
                "provider_account": {
                    "provider_type": "mailbox",
                    "provider_name": "laoudo",
                    "login_identifier": self._email,
                    "display_name": self._email,
                    "credentials": {
                        "authorization": self.auth,
                    },
                    "metadata": {
                        "account_id": self._account_id,
                        "email": self._email,
                    },
                },
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "laoudo",
                    "resource_type": "mailbox",
                    "resource_identifier": self._account_id,
                    "handle": self._email,
                    "display_name": self._email,
                    "metadata": {
                        "account_id": self._account_id,
                        "email": self._email,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            r = curl_requests.get(
                f"{self.api}/list",
                params={"accountId": account.account_id, "allReceive": 0,
                        "emailId": 0, "timeSort": 1, "size": 50, "type": 0},
                headers={"authorization": self.auth, "user-agent": self._ua},
                timeout=15, impersonate="chrome131"
            )
            if r.status_code == 200:
                mails = r.json().get("data", {}).get("list", []) or []
                return {m.get("id") or m.get("emailId") for m in mails if m.get("id") or m.get("emailId")}
        except Exception:
            pass
        return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "trae",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        seen = set(before_ids) if before_ids else set()
        start = time.time()
        h = {"authorization": self.auth, "user-agent": self._ua}
        while time.time() - start < timeout:
            try:
                r = curl_requests.get(
                    f"{self.api}/list",
                    params={"accountId": account.account_id, "allReceive": 0,
                            "emailId": 0, "timeSort": 1, "size": 50, "type": 0},
                    headers=h, timeout=15, impersonate="chrome131"
                )
                if r.status_code == 200:
                    mails = r.json().get("data", {}).get("list", []) or []
                    for mail in mails:
                        mid = mail.get("id") or mail.get("emailId")
                        if not mid or mid in seen:
                            continue
                        seen.add(mid)
                        text = (str(mail.get("subject", "")) + " " +
                                str(mail.get("content") or mail.get("html") or ""))
                        if keyword and keyword.lower() not in text.lower():
                            continue
                        m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', text)
                        if m:
                            return m.group(1) if m.groups() else m.group(0)
            except Exception:
                pass
            time.sleep(4)
        raise TimeoutError(f"Verification code wait timed out ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        seen = set(before_ids or [])
        start = time.time()
        headers = {"authorization": self.auth, "user-agent": self._ua}
        while time.time() - start < timeout:
            try:
                r = curl_requests.get(
                    f"{self.api}/list",
                    params={"accountId": account.account_id, "allReceive": 0,
                            "emailId": 0, "timeSort": 1, "size": 50, "type": 0},
                    headers=headers, timeout=15, impersonate="chrome131"
                )
                if r.status_code == 200:
                    mails = r.json().get("data", {}).get("list", []) or []
                    for mail in mails:
                        mid = mail.get("id") or mail.get("emailId")
                        if not mid or mid in seen:
                            continue
                        seen.add(mid)
                        text = (str(mail.get("subject", "")) + " " +
                                str(mail.get("content") or mail.get("html") or ""))
                        link = extract_verification_link(text, keyword)
                        if link:
                            return link
            except Exception:
                pass
            time.sleep(4)
        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")
