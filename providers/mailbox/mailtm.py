"""MailTmMailbox — register into unified registry."""
from core.mailbox.mailtm import MailTmMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "mailtm_api")(MailTmMailbox)
