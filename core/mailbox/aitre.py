"""mail.aitre.cc temporary mailbox provider."""
import re
import time

import requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link

DEFAULT_AITRE_API_URL = "https://mail.aitre.cc/api/tempmail"


class AitreMailbox(BaseMailbox):
    """mail.aitre.cc temporary mailbox"""
    @classmethod
    def from_config(cls, config: dict) -> 'AitreMailbox':
        return cls(
            email=config.get("aitre_email", ""),
            api_url=config.get("aitre_api_url", ""),
        )

    def __init__(self, email: str, api_url: str = ""):
        self._email = email
        self.api = (api_url or DEFAULT_AITRE_API_URL).rstrip("/")

    def get_email(self) -> MailboxAccount:
        if not self._email:
            raise RuntimeError("Aitre email address is required but not configured. Please set the email address in the provider settings.")
        return MailboxAccount(email=self._email)

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            r = requests.get(f"{self.api}/emails", params={"email": account.email}, timeout=10)
            emails = r.json().get("emails", [])
            return {str(m["id"]) for m in emails if "id" in m}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "trae",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        seen = set(before_ids) if before_ids else set()
        last_check = None
        start = time.time()
        while time.time() - start < timeout:
            params = {"email": account.email}
            if last_check:
                params["lastCheck"] = last_check
            try:
                r = requests.get(f"{self.api}/poll", params=params, timeout=10)
                data = r.json()
                last_check = data.get("lastChecked")
                if data.get("count", 0) > 0:
                    r2 = requests.get(f"{self.api}/emails", params={"email": account.email}, timeout=10)
                    for mail in r2.json().get("emails", []):
                        mid = str(mail.get("id", ""))
                        if mid in seen:
                            continue
                        seen.add(mid)
                        text = mail.get("preview", "") + mail.get("content", "")
                        if keyword and keyword.lower() not in text.lower():
                            continue
                        m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', text)
                        if m:
                            return m.group(1) if m.groups() else m.group(0)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification code wait timed out ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        seen = set(before_ids or [])
        last_check = None
        start = time.time()
        while time.time() - start < timeout:
            params = {"email": account.email}
            if last_check:
                params["lastCheck"] = last_check
            try:
                r = requests.get(f"{self.api}/poll", params=params, timeout=10)
                data = r.json()
                last_check = data.get("lastChecked")
                if data.get("count", 0) > 0:
                    r2 = requests.get(f"{self.api}/emails", params={"email": account.email}, timeout=10)
                    for mail in r2.json().get("emails", []):
                        mid = str(mail.get("id", ""))
                        if mid in seen:
                            continue
                        seen.add(mid)
                        text = str(mail.get("preview", "")) + " " + str(mail.get("content", ""))
                        link = extract_verification_link(text, keyword)
                        if link:
                            return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")
