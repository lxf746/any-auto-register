"""DuckMail — register into unified registry."""
from core.mailbox.duckmail import DuckMailMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "duckmail_api")(DuckMailMailbox)
