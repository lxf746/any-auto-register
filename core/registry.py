"""平台插件注册表 - 自动扫描 platforms/ 目录加载插件"""
import importlib
import json
import pkgutil
from typing import Dict, Type
from sqlmodel import Session, select
from .base_platform import BasePlatform
from .db import PlatformCapabilityOverrideModel, engine

_registry: Dict[str, Type[BasePlatform]] = {}


def _is_missing_plugin_module(exc: ModuleNotFoundError, module_name: str) -> bool:
    return str(getattr(exc, "name", "") or "") == module_name


def register(cls: Type[BasePlatform]):
    """装饰器：注册平台插件"""
    _registry[cls.name] = cls
    return cls


def load_all():
    """自动扫描并加载 platforms/ 下所有插件"""
    import platforms
    for finder, name, _ in pkgutil.iter_modules(platforms.__path__, platforms.__name__ + "."):
        plugin_module = f"{name}.plugin"
        try:
            importlib.import_module(plugin_module)
        except ModuleNotFoundError as exc:
            if _is_missing_plugin_module(exc, plugin_module):
                continue
            raise


def get(name: str) -> Type[BasePlatform]:
    if name not in _registry:
        raise KeyError(f"平台 '{name}' 未注册，已注册: {list(_registry.keys())}")
    return _registry[name]


def list_platforms() -> list:
    overrides: dict[str, dict] = {}
    with Session(engine) as session:
        for item in session.exec(select(PlatformCapabilityOverrideModel)).all():
            overrides[item.platform_name] = item.get_capabilities()
    result = []
    for cls in _registry.values():
        caps = {
            "supported_executors": list(getattr(cls, "supported_executors", ["protocol"])),
            "supported_identity_modes": list(getattr(cls, "supported_identity_modes", ["mailbox"])),
            "supported_oauth_providers": list(getattr(cls, "supported_oauth_providers", [])),
        }
        override = overrides.get(cls.name) or {}
        if isinstance(override, dict):
            caps.update({k: v for k, v in override.items() if k in caps})
        result.append({"name": cls.name, "display_name": cls.display_name,
                       "version": cls.version, **caps})
    return result
