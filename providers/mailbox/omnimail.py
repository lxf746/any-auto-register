"""OmniMailMailbox — register into unified registry."""
from core.base_mailbox import OmniMailMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "omnimail_api")(OmniMailMailbox)
