"""LuckMail — register into unified registry."""
from core.base_mailbox import LuckMailMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "luckmail_api")(LuckMailMailbox)
