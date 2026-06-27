"""Factory for provider_resource dicts used in mailbox extra metadata."""
from typing import Any


def make_provider_resource(
    provider_name: str,
    resource_type: str,
    resource_identifier: str,
    handle: str,
    display_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a provider_resource dict for mailbox extra metadata."""
    return {
        "provider_type": "mailbox",
        "provider_name": provider_name,
        "resource_type": resource_type,
        "resource_identifier": resource_identifier,
        "handle": handle,
        "display_name": display_name or handle,
        "metadata": metadata or {},
    }
