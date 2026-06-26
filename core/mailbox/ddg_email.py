"""DuckDuckGo Email Protection mailbox provider."""
import email as email_lib
import imaplib
import logging
import re
import time

import requests

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount
from core.tls import insecure_request

logger = logging.getLogger(__name__)


class DDGEmailMailbox(BaseMailbox):
    """DuckDuckGo Email Protection — generates @duck.com private alias, reads verification code from forwarding mailbox via IMAP"""

    DDG_API = "https://quack.duckduckgo.com/api/email/addresses"

    # Auto-match common email IMAP addresses
    _IMAP_HOSTS = {
        "163.com": "imap.163.com",
        "126.com": "imap.126.com",
        "qq.com": "imap.qq.com",
        "gmail.com": "imap.gmail.com",
        "outlook.com": "imap-mail.outlook.com",
        "hotmail.com": "imap-mail.outlook.com",
        "yahoo.com": "imap.mail.yahoo.com",
    }

    @classmethod
    def from_config(cls, config: dict) -> 'DDGEmailMailbox':
        return cls(
            bearer=config.get("ddg_bearer", ""),
            imap_host=config.get("ddg_imap_host", ""),
            imap_user=config.get("ddg_imap_user", ""),
            imap_pass=config.get("ddg_imap_pass", ""),
            proxy=config.get("proxy"),
        )

    def __init__(self, bearer: str = "", imap_host: str = "",
                 imap_user: str = "", imap_pass: str = "", proxy: str = None):
        self.bearer = bearer
        self.imap_host = imap_host
        self.imap_user = imap_user
        self.imap_pass = imap_pass
        self.proxy = {"http": proxy, "https": proxy} if proxy else None

        # Auto-detect IMAP host
        if not self.imap_host and self.imap_user and "@" in self.imap_user:
            domain = self.imap_user.split("@", 1)[1].lower()
            self.imap_host = self._IMAP_HOSTS.get(domain, f"imap.{domain}")

    def _headers(self) -> dict:
        return {
            "authorization": f"Bearer {self.bearer}",
            "origin": "https://duckduckgo.com",
            "referer": "https://duckduckgo.com/",
        }

    def get_email(self) -> MailboxAccount:
        r = insecure_request(
            requests.post, self.DDG_API,
            headers=self._headers(),
            proxies=self.proxy,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        address = data.get("address", "")
        if not address:
            raise RuntimeError(f"DDG Email alias creation failed: {r.text[:200]}")
        email = f"{address}@duck.com"
        logger.info("Created alias: %s", email)
        return MailboxAccount(
            email=email,
            account_id=address,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "ddg_email",
                    "resource_type": "mailbox",
                    "resource_identifier": address,
                    "handle": email,
                    "display_name": email,
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        return set()

    def _imap_search_code(self, alias_email: str, timeout: int, code_pattern: str = None) -> str:
        if not self.imap_user or not self.imap_pass:
            raise RuntimeError("DDG Email IMAP not configured (ddg_imap_user / ddg_imap_pass), unable to read verification code")

        pattern = code_pattern or r'(?<!\d)(\d{6})(?!\d)'
        start = time.time()
        seen_ids: set[bytes] = set()
        baseline_done = False

        while time.time() - start < timeout:
            conn = None
            try:
                conn = imaplib.IMAP4_SSL(self.imap_host, 993, timeout=10)
                # 163/126 require sending ID command first
                if any(h in self.imap_host for h in ("163.com", "126.com", "yeah.net")):
                    imaplib.Commands['ID'] = ('NONAUTH', 'AUTH', 'SELECTED')
                    conn._simple_command('ID', '("name" "IMAPClient" "version" "1.0")')
                conn.login(self.imap_user, self.imap_pass)
                conn.select("INBOX", readonly=True)

                _, msg_nums = conn.search(None, "ALL")
                ids = msg_nums[0].split() if msg_nums and msg_nums[0] else []

                # First poll: mark all existing emails as read, only wait for new emails
                if not baseline_done:
                    seen_ids = set(ids)
                    baseline_done = True
                    logger.info("IMAP baseline: %d existing emails skipped", len(seen_ids))
                    conn.logout()
                    conn = None
                    time.sleep(5)
                    continue

                for mid in reversed(ids[-30:]):
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)

                    _, msg_data = conn.fetch(mid, "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)

                    # Check if sent to alias (DDG forwarding preserves original To)
                    to_addr = str(msg.get("To", "") or "").lower()
                    from_addr = str(msg.get("From", "") or "").lower()
                    subject = str(msg.get("Subject", "") or "")

                    # Only look at emails sent to alias or from openai/noreply
                    if alias_email.lower() not in to_addr and "openai" not in from_addr and "noreply" not in from_addr:
                        continue

                    # Extract body
                    body_parts = []
                    if msg.is_multipart():
                        for part in msg.walk():
                            ct = part.get_content_type()
                            if ct in ("text/plain", "text/html"):
                                payload = part.get_payload(decode=True)
                                if payload:
                                    charset = part.get_content_charset() or "utf-8"
                                    body_parts.append(payload.decode(charset, errors="replace"))
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            charset = msg.get_content_charset() or "utf-8"
                            body_parts.append(payload.decode(charset, errors="replace"))

                    combined = subject + " " + " ".join(body_parts)
                    # Remove style/script tag content to avoid matching CSS color values like #000000
                    combined = re.sub(r'<style[^>]*>.*?</style>', '', combined, flags=re.DOTALL | re.IGNORECASE)
                    combined = re.sub(r'<script[^>]*>.*?</script>', '', combined, flags=re.DOTALL | re.IGNORECASE)
                    combined = re.sub(r'<[^>]+>', ' ', combined)
                    m = re.search(pattern, combined)
                    if m:
                        code = m.group(1) if m.groups() else m.group(0)
                        logger.info("IMAP verification code retrieved: %s", code)
                        return code

                conn.logout()
            except (imaplib.IMAP4.error, OSError) as e:
                logger.error("IMAP connection error: %s", e)
            finally:
                if conn:
                    try:
                        conn.logout()
                    except Exception:
                        pass
            time.sleep(5)

        raise TimeoutError(f"DDG Email IMAP verification code wait timed out ({timeout}s)")

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None,
                      code_pattern: str = None) -> str:
        return self._imap_search_code(account.email, timeout, code_pattern)
