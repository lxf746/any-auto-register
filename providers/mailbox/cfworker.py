"""CFWorkerMailbox — register into unified registry."""
from core.mailbox.cfworker import CFWorkerMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "cfworker_admin_api")(CFWorkerMailbox)
