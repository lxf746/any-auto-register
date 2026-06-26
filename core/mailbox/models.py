"""Mailbox models — MailboxAccount dataclass."""
from dataclasses import dataclass, field


@dataclass
class MailboxAccount:
    email: str
    account_id: str = ""
    extra: dict = field(default_factory=dict)
