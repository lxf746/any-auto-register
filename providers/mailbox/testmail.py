"""TestmailMailbox — register into unified registry."""
from core.mailbox.testmail import TestmailMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "testmail_api")(TestmailMailbox)
