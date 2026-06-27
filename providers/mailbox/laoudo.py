"""Laoudo.com — register into unified registry."""
from core.mailbox.laoudo import LaoudoMailbox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "laoudo_api")(LaoudoMailbox)
