"""Mailbox provider configurations — typed dataclasses for provider settings."""
from dataclasses import dataclass, field


@dataclass
class MailboxConfig:
    """Base configuration for all mailbox providers."""
    proxy: str | None = None


@dataclass
class LaoudoConfig(MailboxConfig):
    """Configuration for laoudo.com mailbox service."""
    auth_token: str = ""
    email: str = ""
    account_id: str = ""
    api_url: str = ""


@dataclass
class AitreConfig(MailboxConfig):
    """Configuration for mail.aitre.cc temporary mailbox."""
    email: str = ""
    api_url: str = ""

    def __post_init__(self):
        if not self.email:
            raise ValueError("Aitre email address is required")


@dataclass
class TempMailLolConfig(MailboxConfig):
    """Configuration for tempmail.lol temporary mailbox."""
    api_url: str = ""


@dataclass
class TempMailWebConfig(MailboxConfig):
    """Configuration for temp-mail.org web mailbox."""
    base_url: str = ""


@dataclass
class DuckMailConfig(MailboxConfig):
    """Configuration for duckmail mailbox."""
    api_url: str = ""
    provider_url: str = ""
    bearer: str = ""


@dataclass
class CFWorkerConfig(MailboxConfig):
    """Configuration for Cloudflare Worker mailbox."""
    api_url: str = ""
    admin_token: str = ""
    domain: str = ""
    fingerprint: str = ""


@dataclass
class MoeMailConfig(MailboxConfig):
    """Configuration for MoeMail (sall.cc) mailbox."""
    api_url: str | None = None
    username: str = ""
    password: str = ""
    session_token: str = ""


@dataclass
class FreemailConfig(MailboxConfig):
    """Configuration for freemail (CF Worker) mailbox."""
    api_url: str = ""
    admin_token: str = ""
    username: str = ""
    password: str = ""


@dataclass
class TestmailConfig(MailboxConfig):
    """Configuration for testmail.app mailbox."""
    api_url: str = ""
    api_key: str = ""
    namespace: str = ""
    tag_prefix: str = ""


@dataclass
class DDGEmailConfig(MailboxConfig):
    """Configuration for DuckDuckGo @duck.com mailbox."""
    bearer: str = ""
    imap_host: str = ""
    imap_user: str = ""
    imap_pass: str = ""


@dataclass
class MailTmConfig(MailboxConfig):
    """Configuration for mail.tm mailbox."""
    api_url: str = ""


@dataclass
class TempyEmailConfig(MailboxConfig):
    """Configuration for tempy.email mailbox."""
    api_url: str = ""
