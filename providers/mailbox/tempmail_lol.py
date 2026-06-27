"""TempMail.lol — register into unified registry."""
from core.mailbox.tempmail_lol import TempMailLolMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "tempmail_lol_api")(TempMailLolMailbox)
