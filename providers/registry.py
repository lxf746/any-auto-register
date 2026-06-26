"""Unified provider registry — auto-discovery + factory.

Usage::

    from providers.registry import register_provider, create_provider, load_all

    @register_provider("captcha", "yescaptcha_api")
    class YesCaptcha(BaseCaptcha):
        @classmethod
        def from_config(cls, config: dict) -> 'YesCaptcha':
            ...

    # At startup
    load_all()

    # Runtime creation
    instance = create_provider("captcha", "yescaptcha_api", config)
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
import threading
from typing import Any

logger = logging.getLogger(__name__)

_registry: dict[str, dict[str, type]] = {
    "mailbox": {},
    "captcha": {},
    "sms": {},
    "proxy": {},
}

_loaded = False
_load_lock = threading.Lock()


def register_provider(provider_type: str, driver_type: str):
    """Decorator that registers a provider class in the global registry."""
    def decorator(cls):
        _registry.setdefault(provider_type, {})[driver_type] = cls
        return cls
    return decorator


def get_provider_class(provider_type: str, driver_type: str) -> type | None:
    """Look up a registered provider class.  Returns *None* if not found."""
    return _registry.get(provider_type, {}).get(driver_type)


def create_provider(provider_type: str, driver_type: str, config: dict) -> Any:
    """Unified factory — create a provider instance from DB config.

    The provider class must expose a ``from_config(config)`` classmethod.
    """
    cls = get_provider_class(provider_type, driver_type)
    if cls is None:
        raise ValueError(f"Unregistered provider: {provider_type}/{driver_type}")
    factory = getattr(cls, "from_config", None)
    if factory is None:
        raise TypeError(f"{cls.__name__} missing from_config classmethod")
    return factory(config)


def list_registered(provider_type: str) -> dict[str, type]:
    """Return ``{driver_type: cls}`` for a given provider type."""
    return dict(_registry.get(provider_type, {}))


def load_all() -> None:
    """Scan and import every provider module under ``providers/``."""
    global _loaded
    with _load_lock:
        if _loaded:
            return

        import providers.captcha
        import providers.proxy
        import providers.sms
        import providers.mailbox

        for package in (providers.captcha, providers.proxy, providers.sms, providers.mailbox):
            for _finder, name, _ispkg in pkgutil.iter_modules(
                package.__path__, package.__name__ + "."
            ):
                try:
                    importlib.import_module(name)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to load provider module %s: %s", name, exc)

        _loaded = True
