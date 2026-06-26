"""testmail.app email service provider."""
import random
import re
import string
import time

import requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link, normalize_api_base_url


class TestmailMailbox(BaseMailbox):
    """testmail.app email service, address format is {namespace}.{tag}@inbox.testmail.app."""

    def __init__(
        self,
        api_url: str = "",
        api_key: str = "",
        namespace: str = "",
        tag_prefix: str = "",
        proxy: str = None,
    ):
        self.api = normalize_api_base_url(api_url, default="", label="Testmail API URL")
        self.api_key = str(api_key or "").strip()
        self.namespace = str(namespace or "").strip()
        self.tag_prefix = str(tag_prefix or "").strip().strip(".")
        self.proxy = {"http": proxy, "https": proxy} if proxy else None

    def _assert_ready(self) -> None:
        if not self.api_key:
            raise RuntimeError("Testmail API Key not configured")
        if not self.namespace:
            raise RuntimeError("Testmail namespace not configured")

    def _build_tag(self) -> str:
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"{self.tag_prefix}.{suffix}" if self.tag_prefix else suffix

    def _query_inbox(
        self,
        *,
        tag: str,
        timestamp_from: int | None,
        livequery: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        params = {
            "apikey": self.api_key,
            "namespace": self.namespace,
            "tag": tag,
            "limit": limit,
        }
        if timestamp_from is not None:
            params["timestamp_from"] = int(timestamp_from)
        if livequery:
            params["livequery"] = "true"
        response = requests.get(self.api, params=params, proxies=self.proxy, timeout=15)
        payload = response.json()
        if payload.get("result") == "fail":
            raise RuntimeError(f"Testmail query failed: {payload.get('message') or response.text}")
        return payload.get("emails", []) or []

    @staticmethod
    def _message_id(mail: dict) -> str:
        return str(
            mail.get("id")
            or mail.get("message_id")
            or f"{mail.get('timestamp', '')}:{mail.get('tag', '')}:{mail.get('subject', '')}"
        )

    @staticmethod
    def _message_text(mail: dict) -> str:
        return " ".join(
            str(mail.get(key, "") or "")
            for key in ("subject", "text", "html")
        )

    def get_email(self) -> MailboxAccount:
        self._assert_ready()
        tag = self._build_tag()
        email = f"{self.namespace}.{tag}@inbox.testmail.app"
        created_at_ms = int(time.time() * 1000)
        return MailboxAccount(
            email=email,
            account_id=tag,
            extra={
                "provider_account": {
                    "provider_type": "mailbox",
                    "provider_name": "testmail",
                    "login_identifier": self.namespace,
                    "display_name": self.namespace,
                    "credentials": {
                        "api_key": self.api_key,
                    },
                    "metadata": {
                        "api_url": self.api,
                        "namespace": self.namespace,
                        "tag_prefix": self.tag_prefix,
                    },
                },
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "testmail",
                    "resource_type": "mailbox",
                    "resource_identifier": email,
                    "handle": email,
                    "display_name": email,
                    "metadata": {
                        "email": email,
                        "namespace": self.namespace,
                        "tag": tag,
                        "api_url": self.api,
                        "created_at_ms": created_at_ms,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        tag = str(account.account_id or "")
        if not tag:
            return set()
        started = ((account.extra or {}).get("provider_resource") or {}).get("metadata", {}).get("created_at_ms")
        try:
            mails = self._query_inbox(tag=tag, timestamp_from=started, limit=20)
            return {self._message_id(mail) for mail in mails if self._message_id(mail)}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        tag = str(account.account_id or "")
        if not tag:
            raise RuntimeError("Testmail mailbox missing tag")
        seen = set(before_ids or [])
        started = ((account.extra or {}).get("provider_resource") or {}).get("metadata", {}).get("created_at_ms")
        pattern = re.compile(code_pattern) if code_pattern else None
        start = time.time()
        while time.time() - start < timeout:
            try:
                mails = self._query_inbox(tag=tag, timestamp_from=started, limit=20)
                for mail in sorted(mails, key=lambda item: item.get("timestamp", 0), reverse=True):
                    mid = self._message_id(mail)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = self._message_text(mail)
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
                    match = pattern.search(text) if pattern else re.search(r'(?<!#)(?<!\d)(\d{6})(?!\d)', text)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification code wait timed out ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        tag = str(account.account_id or "")
        if not tag:
            raise RuntimeError("Testmail mailbox missing tag")
        seen = set(before_ids or [])
        started = ((account.extra or {}).get("provider_resource") or {}).get("metadata", {}).get("created_at_ms")
        start = time.time()
        while time.time() - start < timeout:
            try:
                mails = self._query_inbox(tag=tag, timestamp_from=started, limit=20)
                for mail in sorted(mails, key=lambda item: item.get("timestamp", 0), reverse=True):
                    mid = self._message_id(mail)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    link = extract_verification_link(self._message_text(mail), keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")
