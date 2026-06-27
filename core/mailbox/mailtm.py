"""mail.tm free temporary mailbox (auto-generated, no configuration required)."""
from __future__ import annotations

import random
import re
import string
import time

import requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link

DEFAULT_MAILTM_API_URL = "https://api.mail.tm"


class MailTmMailbox(BaseMailbox):
    """mail.tm free temporary mailbox (auto-generated, no configuration required)."""

    def __init__(self, proxy: str = None, api_url: str = ""):
        self.api = (api_url or DEFAULT_MAILTM_API_URL).rstrip("/")
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._token = None
        self._email = None
        self._id = None

    @classmethod
    def from_config(cls, config: dict) -> "MailTmMailbox":
        from core.mailbox.config import MailTmConfig
        cfg = MailTmConfig(
            api_url=config.get("mailtm_api_url", ""),
            proxy=config.get("proxy") or None,
        )
        return cls(
            api_url=cfg.api_url,
            proxy=cfg.proxy,
        )

    def _mailtm_request(self, method, path, json_data=None, headers=None):
        url = f"{self.api}{path}"
        h = headers or {}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        resp = requests.request(method, url, json=json_data, headers=h, proxies=self.proxy, timeout=15)
        resp.raise_for_status()
        return resp

    def get_email(self) -> MailboxAccount:
        r = self._mailtm_request("GET", "/domains")
        domains = r.json().get("hydra:member", [])
        if not domains:
            raise RuntimeError("mail.tm: no available domains")
        domain = random.choice(domains)["domain"]
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        password = "".join(random.choices(string.ascii_letters + string.digits, k=12))
        email = f"{username}@{domain}"
        self._mailtm_request("POST", "/accounts", json_data={"address": email, "password": password})
        r = self._mailtm_request("POST", "/token", json_data={"address": email, "password": password})
        self._token = r.json().get("token")
        self._email = email
        self._id = r.json().get("id")
        return MailboxAccount(
            email=self._email,
            account_id=self._email,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "mailtm",
                    "resource_type": "mailbox",
                    "resource_identifier": self._token,
                    "handle": self._email,
                    "display_name": self._email,
                    "metadata": {
                        "email": self._email,
                        "token": self._token,
                        "password": password,
                    },
                },
            },
        )

    def _get_mailtm_token(self, account: MailboxAccount) -> str:
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
                    msg_r = requests.get(f"{self.api}/messages/{mid}",
                        headers={"Authorization": f"Bearer {token}"},
                        proxies=self.proxy, timeout=10)
                    msg = msg_r.json()
                    text = str(msg.get("subject", "")) + " " + str(msg.get("text", "")) + " " + str(msg.get("html", ""))
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    pattern = code_pattern or r"(?<!#)(?<!\d)(\d{6})(?!\d)"
                    m = re.search(pattern, text)
                    if m:
                        return m.group(1) if m.groups() else m.group(0)
            except Exception:
                pass
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
