"""TempMailWebMailbox — register into unified registry."""
from core.mailbox.tempmail_web import TempMailWebMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "tempmail_web_api")(TempMailWebMailbox)
