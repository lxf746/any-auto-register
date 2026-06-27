"""MoeMailMailbox — register into unified registry."""
from core.mailbox.moemail import MoeMailMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "moemail_api")(MoeMailMailbox)
