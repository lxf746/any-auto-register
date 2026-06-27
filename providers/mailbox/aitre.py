"""AitreMailbox — register into unified registry."""
from core.mailbox.aitre import AitreMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "aitre_api")(AitreMailbox)
