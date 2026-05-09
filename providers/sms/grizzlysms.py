"""GrizzlySMS provider plugin registration."""

from core.base_sms import GrizzlySmsProvider  # noqa: F401
from providers.registry import register_provider

register_provider("sms", "grizzlysms_api")(GrizzlySmsProvider)
