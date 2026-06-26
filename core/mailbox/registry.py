"""Mailbox provider registry — create_mailbox entry point using unified registry."""
import logging

from core.mailbox.base import BaseMailbox, FallbackMailbox

logger = logging.getLogger(__name__)


def create_mailbox(provider: str, extra: dict = None, proxy: str = None) -> BaseMailbox:
    """Factory method: create a mailbox instance based on provider.

    Uses the unified provider registry (providers.registry) for class lookup.
    """
    from providers.registry import create_provider, get_provider_class

    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository
    from infrastructure.provider_settings_repository import ProviderSettingsRepository

    definitions_repo = ProviderDefinitionsRepository()
    settings_repo = ProviderSettingsRepository()
    provider_key = str(provider or "").strip()
    if not provider_key:
        raise RuntimeError("No mailbox provider selected, please configure and enable a default mailbox provider in settings")
    definition = definitions_repo.get_by_key("mailbox", provider_key)
    if not definition or not definition.enabled:
        raise RuntimeError(f"Mailbox provider does not exist or is disabled: {provider_key}")
    base_extra = dict(extra or {})

    raw_fallbacks = base_extra.get("mail_provider_fallbacks")
    explicit_fallbacks: list[str] = []
    if isinstance(raw_fallbacks, str):
        explicit_fallbacks = [item.strip() for item in raw_fallbacks.split(",") if item.strip()]
    elif isinstance(raw_fallbacks, (list, tuple, set)):
        explicit_fallbacks = [str(item or "").strip() for item in raw_fallbacks if str(item or "").strip()]

    enabled_items = settings_repo.list_enabled("mailbox")
    enabled_keys = [str(item.provider_key or "").strip() for item in enabled_items if str(item.provider_key or "").strip()]
    ordered_keys: list[str] = [provider_key]
    for key in explicit_fallbacks:
        if key not in ordered_keys:
            ordered_keys.append(key)
    for key in enabled_keys:
        if key == provider_key or key == "laoudo" or key in ordered_keys:
            continue
        ordered_keys.append(key)

    providers: list[tuple[str, BaseMailbox]] = []
    for key in ordered_keys:
        current_definition = definitions_repo.get_by_key("mailbox", key)
        if not current_definition or not current_definition.enabled:
            continue
        resolved_extra = settings_repo.resolve_runtime_settings("mailbox", key, base_extra)
        lookup_key = current_definition.driver_type if current_definition else key

        # Use unified registry for class lookup
        cls = get_provider_class("mailbox", lookup_key)
        if cls is None:
            logger.warning("Mailbox provider %s not found in registry, skipped", lookup_key)
            continue

        try:
            # Add proxy to resolved_extra for from_config()
            config = dict(resolved_extra)
            if proxy and "proxy" not in config:
                config["proxy"] = proxy

            # Special handling for generic_http_mailbox (needs pipeline_config)
            if lookup_key in ("generic_http_mailbox", "generic_http"):
                pipeline_config = current_definition.get_metadata() if current_definition else {}
                instance = cls.from_config({**config, "pipeline_config": pipeline_config})
            else:
                instance = cls.from_config(config)
            providers.append((key, instance))
        except Exception as exc:
            if key == provider_key:
                raise RuntimeError(f"Mailbox provider {key} initialization failed: {exc}") from exc
            logger.warning("Mailbox provider %s initialization failed, skipped: %s", key, exc)

    if not providers:
        raise RuntimeError("No available mailbox provider instances")
    if len(providers) == 1:
        return providers[0][1]
    return FallbackMailbox(providers)
