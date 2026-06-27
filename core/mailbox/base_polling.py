"""Base class for polling-based mailbox providers."""
import re
import time
import logging
from abc import abstractmethod

from core.mailbox.base import BaseMailbox
from core.mailbox.models import MailboxAccount

logger = logging.getLogger(__name__)

DEFAULT_CODE_PATTERN = r'(?<!#)(?<!\d)(\d{6})(?!\d)'


class BasePollingMailbox(BaseMailbox):
    """Base class for mailboxes that poll for messages."""

    POLL_INTERVAL: int = 5
    DEFAULT_TIMEOUT: int = 300
    CODE_PATTERN: str = DEFAULT_CODE_PATTERN

    @abstractmethod
    def _fetch_messages(self, account: MailboxAccount) -> list[dict]:
        """Fetch messages from the mailbox. Subclasses must implement."""
        ...

    @abstractmethod
    def _message_id(self, message: dict) -> str:
        """Extract unique ID from a message dict. Subclasses must implement."""
        ...

    @abstractmethod
    def _message_text(self, message: dict) -> str:
        """Extract searchable text from a message dict. Subclasses must implement."""
        ...

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            return {
                self._message_id(msg)
                for msg in self._fetch_messages(account)
                if self._message_id(msg)
            }
        except Exception:
            return set()

    def wait_for_code(
        self,
        account: MailboxAccount,
        keyword: str = "",
        timeout: int | None = None,
        before_ids: set[str] | None = None,
        code_pattern: str | None = None,
    ) -> str:
        timeout = timeout or self.DEFAULT_TIMEOUT
        pattern = re.compile(code_pattern or self.CODE_PATTERN)
        seen = set(before_ids or [])
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                messages = self._fetch_messages(account)
                for msg in messages:
                    mid = self._message_id(msg)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = self._message_text(msg)
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    match = pattern.search(text)
                    if match:
                        return match.group(1) if match.lastindex else match.group(0)
            except Exception as e:
                logger.debug("Poll error: %s", e)
            time.sleep(self.POLL_INTERVAL)

        raise TimeoutError(f"Verification code wait timed out ({timeout}s)")

    def wait_for_link(
        self,
        account: MailboxAccount,
        keyword: str = "",
        timeout: int | None = None,
        before_ids: set[str] | None = None,
    ) -> str:
        timeout = timeout or self.DEFAULT_TIMEOUT
        seen = set(before_ids or [])
        deadline = time.time() + timeout
        link_pattern = r'https?://[^\s<>"]+'

        while time.time() < deadline:
            try:
                messages = self._fetch_messages(account)
                for msg in messages:
                    mid = self._message_id(msg)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = self._message_text(msg)
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    match = re.search(link_pattern, text)
                    if match:
                        return match.group(0)
            except Exception as e:
                logger.debug("Poll error: %s", e)
            time.sleep(self.POLL_INTERVAL)

        raise TimeoutError(f"Verification link wait timed out ({timeout}s)")
