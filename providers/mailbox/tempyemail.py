"""Tempy.Email — free temporary mailbox (no registration, no auth)."""
from core.base_mailbox import BaseMailbox, MailboxAccount
from providers.registry import register_provider

TEMP_API = "https://tempy.email/api/v1"


class TempyMailbox(BaseMailbox):
    def __init__(self, proxy: str | None = None, api_url: str = ""):
        self.api = (api_url or TEMP_API).rstrip("/")
        self.proxy = {"http": proxy, "https": proxy} if proxy else None

    @classmethod
    def from_config(cls, config: dict):
        return cls(proxy=config.get("proxy"), api_url=config.get("tempyemail_api_url", ""))

    def get_email(self) -> MailboxAccount:
        import requests
        r = requests.post(f"{self.api}/mailbox", json={},
                          proxies=self.proxy, timeout=15)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"tempy.email create inbox failed: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        email = data.get("email", "")
        if not email:
            raise RuntimeError(f"tempy.email: empty email in response: {data}")
        return MailboxAccount(
            email=email,
            account_id=email,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "tempyemail",
                    "resource_type": "mailbox",
                    "resource_identifier": email,
                    "handle": email,
                    "display_name": email,
                    "metadata": {"email": email},
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        import requests
        try:
            email = account.email
            r = requests.get(f"{self.api}/mailbox/{email}/messages",
                             proxies=self.proxy, timeout=10)
            if r.status_code != 200:
                return set()
            return {str(m.get("id", "")) for m in r.json().get("messages", []) if m.get("id")}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set | None = None,
                      code_pattern: str | None = None) -> str:
        import re, time, requests
        email = account.email
        if not email:
            raise RuntimeError("tempy.email: missing email in account")
        seen = set(before_ids or [])
        start = time.time()
        default_pattern = code_pattern or r"(?<!#)(?<!\d)(\d{6})(?!\d)"
        kw_lower = keyword.lower() if keyword else ""

        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.api}/mailbox/{email}/messages",
                                 proxies=self.proxy, timeout=10)
                if r.status_code == 200:
                    for msg in r.json().get("messages", []):
                        mid = str(msg.get("id", ""))
                        if mid in seen:
                            continue
                        seen.add(mid)
                        body = (str(msg.get("body_text", "") or "") +
                                str(msg.get("text", "") or "") +
                                str(msg.get("html", "") or "") +
                                str(msg.get("subject", "") or ""))
                        if kw_lower and kw_lower not in body.lower():
                            continue
                        m = re.search(default_pattern, body)
                        if m:
                            return m.group(1)
                time.sleep(3)
            except Exception:
                time.sleep(3)
        raise TimeoutError(f"tempy.email: no verification code found in {timeout}s")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set | None = None) -> str:
        import re, time, requests
        email = account.email
        if not email:
            raise RuntimeError("tempy.email: missing email in account")
        seen = set(before_ids or [])
        start = time.time()
        kw_lower = keyword.lower() if keyword else ""
        url_pat = re.compile(r'https?://[^\s"\'<>&]+')

        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.api}/mailbox/{email}/messages",
                                 proxies=self.proxy, timeout=10)
                if r.status_code == 200:
                    for msg in r.json().get("messages", []):
                        mid = str(msg.get("id", ""))
                        if mid in seen:
                            continue
                        seen.add(mid)
                        body = (str(msg.get("body_text", "") or "") +
                                str(msg.get("html", "") or "") +
                                str(msg.get("text", "") or "") +
                                str(msg.get("subject", "") or ""))
                        if kw_lower and kw_lower not in body.lower():
                            continue
                        urls = url_pat.findall(body)
                        if urls:
                            return urls[0]
                time.sleep(3)
            except Exception:
                time.sleep(3)
        raise TimeoutError(f"tempy.email: no verification link found in {timeout}s")


register_provider("mailbox", "tempyemail_api")(TempyMailbox)
