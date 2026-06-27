"""TempyMailbox — register into unified registry."""
from core.mailbox.tempyemail import TempyMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "tempyemail_api")(TempyMailbox)
