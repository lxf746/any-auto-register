"""Same Temp-Mail Web API provider."""
import json
import logging
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.mailbox.utils import extract_verification_link, normalize_api_base_url

logger = logging.getLogger(__name__)

DEFAULT_TEMPMAIL_WEB_BASE_URL = "https://web2.temp-mail.org"


class TempMailWebMailbox(BaseMailbox):
    """Same Temp-Mail Web API as the reference project."""

    @classmethod
    def from_config(cls, config: dict) -> 'TempMailWebMailbox':
        from core.mailbox.config import TempMailWebConfig
        cfg = TempMailWebConfig(
            base_url=config.get("tempmail_web_base_url", ""),
            proxy=config.get("proxy"),
        )
        return cls(
            base_url=cfg.base_url,
            proxy=cfg.proxy,
        )

    def __init__(self, base_url: str = "", proxy: str = None):
        self.base_url = normalize_api_base_url(
            base_url,
            default=DEFAULT_TEMPMAIL_WEB_BASE_URL,
            label="Temp-Mail Web URL",
        )
        self.proxy = str(proxy or "").strip()
        self._accounts: dict[str, str] = {}
        self._executor = None
        self._browser = None
        self._page = None

    def _ensure_browser(self):
        if self._page is not None:
            return self._page
        from camoufox.sync_api import Camoufox

        launch_opts = {"headless": True}
        if self.proxy:
            parsed = urlparse(self.proxy)
            if parsed.scheme and parsed.hostname and parsed.port:
                proxy_config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
                if parsed.username:
                    proxy_config["username"] = parsed.username
                if parsed.password:
                    proxy_config["password"] = parsed.password
                launch_opts["proxy"] = proxy_config
            else:
                launch_opts["proxy"] = {"server": self.proxy}
            launch_opts["geoip"] = True
        self._browser = Camoufox(**launch_opts)
        browser = self._browser.__enter__()
        self._page = browser.new_page()
        self._page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        return self._page

    def _run_in_browser_thread(self, fn):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tempmail-web")
        future = self._executor.submit(fn)
        return future.result()

    @staticmethod
    def _decode_json_response(response: dict, action: str):
        status = int((response or {}).get("status", 0) or 0)
        text = str((response or {}).get("body", "") or "")
        if status != 200:
            raise RuntimeError(
                f"Temp-Mail Web {action} failed: HTTP {status} {text[:300]}"
            )
        try:
            return json.loads(text)
        except Exception as exc:
            raise RuntimeError(
                f"Temp-Mail Web {action} returned non-JSON: {exc}; body={text[:300]}"
            ) from exc

    def _request_json(self, method: str, path: str, *, auth_header: str = "") -> dict | list:
        target_url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        action = "create mailbox" if path.lstrip("/") == "mailbox" else "fetch messages"
        max_attempts = 4 if path.lstrip("/") == "mailbox" else 2

        for attempt in range(1, max_attempts + 1):
            def _browser_call():
                page = self._ensure_browser()
                return page.evaluate(
                    """
                    async ({ targetUrl, method, authHeader, baseUrl }) => {
                      try {
                        const response = await fetch(targetUrl, {
                          method,
                          credentials: 'include',
                          referrer: baseUrl,
                          headers: {
                            'Accept': 'application/json',
                            ...(method === 'GET' ? { 'Cache-Control': 'no-cache' } : {}),
                            ...(authHeader ? { 'Authorization': authHeader } : {}),
                          },
                          ...(method === 'POST' ? { body: '{}' } : {}),
                        });
                        return {
                          status: response.status,
                          body: await response.text(),
                        };
                      } catch (error) {
                        return {
                          status: 0,
                          body: error instanceof Error ? error.message : String(error),
                        };
                      }
                    }
                    """,
                    {
                        "targetUrl": target_url,
                        "method": method,
                        "authHeader": auth_header,
                        "baseUrl": self.base_url,
                    },
                )

            result = self._run_in_browser_thread(_browser_call)
            status = int((result or {}).get("status", 0) or 0)
            if status != 429 or attempt >= max_attempts:
                return self._decode_json_response(result, action)
            wait_seconds = min(20, 3 * attempt + random.uniform(0.5, 2.5))
            logger.warning("%s encountered 429, retrying in %.1fs (%d/%d)", action, wait_seconds, attempt, max_attempts)
            time.sleep(wait_seconds)

        return self._decode_json_response(result, action)

    def get_email(self) -> MailboxAccount:
        data = self._request_json("POST", "/mailbox")
        address = str(data.get("address") or data.get("mailbox") or data.get("email") or "").strip()
        token = str(data.get("token") or "").strip()
        if not address or not token:
            raise RuntimeError(f"Temp-Mail Web create mailbox failed: {json.dumps(data, ensure_ascii=False)[:300]}")
        self._accounts[address] = token
        logger.info("Generated mailbox: %s", address)
        return MailboxAccount(
            email=address,
            account_id=token,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "tempmail_web",
                    "resource_type": "mailbox",
                    "resource_identifier": token,
                    "handle": address,
                    "display_name": address,
                    "metadata": {
                        "email": address,
                        "token": token,
                        "base_url": self.base_url,
                    },
                },
            },
        )

    def _fetch_messages(self, account: MailboxAccount) -> list[dict]:
        token = str(account.account_id or self._accounts.get(account.email) or "").strip()
        if not token:
            raise RuntimeError(f"Temp-Mail Web missing token: {account.email}")
        data = self._request_json("GET", "/messages", auth_header=f"Bearer {token}")
        if isinstance(data, dict) and isinstance(data.get("messages"), list):
            return list(data.get("messages") or [])
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _message_id(message: dict) -> str:
        return str(
            message.get("id")
            or message.get("_id")
            or f"{message.get('createdAt', '')}:{message.get('subject', '')}"
        )

    @staticmethod
    def _extract_code(message: dict, code_pattern: str | None = None) -> str:
        subject = str(message.get("subject") or "").strip()
        if subject:
            last_token = subject.split()[-1]
            if re.fullmatch(r"\d{6}", last_token):
                return last_token
        text = " ".join(
            str(message.get(key) or "")
            for key in ("subject", "body", "text", "content", "html")
        )
        match = re.search(code_pattern or r"(?<!#)(?<!\d)(\d{6})(?!\d)", text)
        if not match:
            return ""
        return match.group(1) if match.groups() else match.group(0)

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            return {
                self._message_id(item)
                for item in self._fetch_messages(account)
                if self._message_id(item)
            }
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                messages = self._fetch_messages(account)
                for item in messages:
                    mid = self._message_id(item)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = " ".join(
                        str(item.get(key) or "")
                        for key in ("subject", "body", "text", "content", "html")
                    )
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    code = self._extract_code(item, code_pattern=code_pattern)
                    if code:
                        logger.debug("Received verification code: %s", code)
                        return code
            except Exception:
                pass
            time.sleep(5)
        raise TimeoutError(f"Verification code wait timed out ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                messages = self._fetch_messages(account)
                for item in messages:
                    mid = self._message_id(item)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = " ".join(
                        str(item.get(key) or "")
                        for key in ("subject", "body", "text", "content", "html")
                    )
                    link = extract_verification_link(text, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(5)
        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")

    def __del__(self):
        executor = getattr(self, "_executor", None)
        browser = getattr(self, "_browser", None)
        if executor is not None and browser is not None:
            try:
                executor.submit(browser.__exit__, None, None, None).result(timeout=5)
            except Exception:
                pass
        if executor is not None:
            try:
                executor.shutdown(wait=False, cancel_futures=False)
            except Exception:
                pass
