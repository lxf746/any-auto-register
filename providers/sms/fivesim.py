"""5sim provider — register into unified registry."""

from core.base_sms import FiveSimProvider
from providers.registry import register_provider

register_provider("sms", "fivesim_api")(FiveSimProvider)

