"""Platform plugin registry - auto-scan platforms/ directory to load plugins"""
import importlib
import pkgutil
import threading
from typing import Dict, Type
from sqlmodel import Session, select
from .base_platform import BasePlatform
from .db import PlatformCapabilityOverrideModel, engine
from core.datetime_utils import _utcnow

_registry: Dict[str, Type[BasePlatform]] = {}
_registry_lock = threading.RLock()
_loaded = False

_CAPABILITY_KEYS = ("supported_executors", "supported_identity_modes", "supported_oauth_providers", "capabilities")


def register(cls: Type[BasePlatform]):
    """Decorator: register a platform plugin"""
    with _registry_lock:
        _registry[cls.name] = cls
    return cls


def load_all():
    """Auto-scan and load all plugins under platforms/"""
    global _loaded
    with _registry_lock:
        if _loaded:
            return
        import platforms
        for finder, name, _ in pkgutil.iter_modules(platforms.__path__, platforms.__name__ + "."):
            try:
                importlib.import_module(f"{name}.plugin")
            except ModuleNotFoundError:
                pass
        _loaded = True


def get(name: str) -> Type[BasePlatform]:
    with _registry_lock:
        if name not in _registry:
            raise KeyError(f"Platform '{name}' is not registered, registered: {list(_registry.keys())}")
        return _registry[name]


def _class_defaults(cls: Type[BasePlatform]) -> dict[str, list[str]]:
    """Get fallback defaults from class attributes (only used when DB has no data)."""
    return {
        "supported_executors": list(getattr(cls, "supported_executors", [])),
        "supported_identity_modes": list(getattr(cls, "supported_identity_modes", [])),
        "supported_oauth_providers": list(getattr(cls, "supported_oauth_providers", [])),
        "capabilities": list(getattr(cls, "capabilities", [])),
    }


def _normalize_platform_capabilities(data: dict | None, cls: Type[BasePlatform]) -> dict[str, list[str]]:
    defaults = _class_defaults(cls)
    payload = data if isinstance(data, dict) else {}
    normalized: dict[str, list[str]] = {}
    for key in _CAPABILITY_KEYS:
        raw = payload.get(key)
        if isinstance(raw, list):
            normalized[key] = [str(item) for item in raw if str(item or "").strip()]
        else:
            normalized[key] = list(defaults.get(key, []))
    return normalized


def _ensure_platform_capabilities_seeded(session: Session) -> dict[str, PlatformCapabilityOverrideModel]:
    items = session.exec(select(PlatformCapabilityOverrideModel)).all()
    by_name = {item.platform_name: item for item in items}
    changed = False
    for cls in _registry.values():
        if cls.name in by_name:
            item = by_name[cls.name]
            current = _normalize_platform_capabilities(item.get_capabilities(), cls)
            defaults = _class_defaults(cls)
            merged = {key: list(current.get(key, [])) for key in _CAPABILITY_KEYS}
            did_merge = False
            for key in _CAPABILITY_KEYS:
                for value in defaults.get(key, []):
                    if value not in merged[key]:
                        merged[key].append(value)
                        did_merge = True
            if did_merge:
                item.set_capabilities(merged)
                item.updated_at = _utcnow()
                session.add(item)
                changed = True
            continue
        item = PlatformCapabilityOverrideModel(platform_name=cls.name)
        item.created_at = _utcnow()
        item.updated_at = _utcnow()
        item.set_capabilities(_class_defaults(cls))
        session.add(item)
        by_name[cls.name] = item
        changed = True
    if changed:
        session.commit()
        items = session.exec(select(PlatformCapabilityOverrideModel)).all()
        by_name = {item.platform_name: item for item in items}
    return by_name


def get_platform_capabilities(name: str) -> dict[str, list[str]]:
    cls = get(name)
    with Session(engine) as session:
        by_name = _ensure_platform_capabilities_seeded(session)
        item = by_name.get(name)
        if item:
            return _normalize_platform_capabilities(item.get_capabilities(), cls)
    return _class_defaults(cls)


def list_platforms() -> list:
    with _registry_lock:
        with Session(engine) as session:
            persisted = _ensure_platform_capabilities_seeded(session)
            result = []
            for cls in _registry.values():
                item = persisted.get(cls.name)
                caps = _normalize_platform_capabilities(item.get_capabilities() if item else None, cls)
                result.append({
                    "name": cls.name,
                    "display_name": cls.display_name,
                    "version": cls.version,
                    **caps,
                })
            return result
