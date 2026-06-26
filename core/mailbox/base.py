"""Base mailbox abstractions — BaseMailbox ABC and FallbackMailbox."""
from abc import ABC, abstractmethod
import logging

from core.mailbox.models import MailboxAccount

logger = logging.getLogger(__name__)


class BaseMailbox(ABC):
    @abstractmethod
    def get_email(self) -> MailboxAccount:
        """Get an available mailbox"""
        ...

    @abstractmethod
    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None,
                      code_pattern: str = None) -> str:
        """Wait and return verification code, code_pattern is a custom regex (default matches 6-digit numbers)"""
        ...

    @abstractmethod
    def get_current_ids(self, account: MailboxAccount) -> set:
        """Return current message ID set (used to filter old messages)"""
        ...

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        """Wait and return verification link. Concrete provider should implement this."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support wait_for_link() yet")


class FallbackMailbox(BaseMailbox):
    """Try multiple providers in order, stick to the same provider after successful creation."""

    def __init__(self, providers: list[tuple[str, 'BaseMailbox']]):
        self.providers = [(str(key or "").strip(), mailbox) for key, mailbox in providers if str(key or "").strip() and mailbox]
        self._accounts: dict[str, BaseMailbox] = {}

    @staticmethod
    def _inject_provider_metadata(account: MailboxAccount, provider_key: str) -> MailboxAccount:
        account.extra = dict(account.extra or {})
        account.extra["mailbox_provider_key"] = provider_key
        provider_resource = dict((account.extra.get("provider_resource") or {}))
        if provider_resource and not provider_resource.get("provider_name"):
            provider_resource["provider_name"] = provider_key
            account.extra["provider_resource"] = provider_resource
        return account

    def _resolve_mailbox(self, account: MailboxAccount) -> BaseMailbox:
        provider_key = str((account.extra or {}).get("mailbox_provider_key") or "").strip()
        if provider_key:
            for key, mailbox in self.providers:
                if key == provider_key:
                    return mailbox
        mailbox = self._accounts.get(str(account.email or "").strip())
        if mailbox is not None:
            return mailbox
        raise RuntimeError(f"Mailbox provider context not found: {account.email}")

    def get_email(self) -> MailboxAccount:
        errors: list[str] = []
        for provider_key, mailbox in self.providers:
            try:
                logger.info("Trying provider: %s", provider_key)
                account = mailbox.get_email()
                self._accounts[str(account.email or "").strip()] = mailbox
                self._inject_provider_metadata(account, provider_key)
                logger.info("Provider succeeded: %s -> %s", provider_key, account.email)
                return account
            except Exception as exc:
                message = str(exc).strip() or exc.__class__.__name__
                errors.append(f"{provider_key}: {message}")
                logger.warning("Provider failed: %s -> %s", provider_key, message)
                continue
        raise RuntimeError("All mailbox providers failed: " + " | ".join(errors))

    def get_current_ids(self, account: MailboxAccount) -> set:
        return self._resolve_mailbox(account).get_current_ids(account)

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None,
                      code_pattern: str = None) -> str:
        return self._resolve_mailbox(account).wait_for_code(
            account,
            keyword=keyword,
            timeout=timeout,
            before_ids=before_ids,
            code_pattern=code_pattern,
        )

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        return self._resolve_mailbox(account).wait_for_link(
            account,
            keyword=keyword,
            timeout=timeout,
            before_ids=before_ids,
        )
