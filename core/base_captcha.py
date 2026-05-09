"""验证码解决器基类 — 具体实现已迁移到 providers/captcha/"""
from abc import ABC, abstractmethod


class BaseCaptcha(ABC):
    @abstractmethod
    def solve_turnstile(self, page_url: str, site_key: str) -> str:
        """返回 Turnstile token"""
        ...

    @abstractmethod
    def solve_image(self, image_b64: str) -> str:
        """返回图片验证码文字"""
        ...

    def solve_cloudflare5s(self, website_url: str, *, proxy: str, rq_data: dict | None = None) -> dict:
        """可选：返回 CloudFlare5s 结果（cookies/headers/tls 等）"""
        raise NotImplementedError("当前验证码 provider 不支持 CloudFlare5s")


# ---------------------------------------------------------------------------
# Lazy re-exports for backward compatibility
# (concrete classes now live under providers/captcha/)
# ---------------------------------------------------------------------------
_LAZY_IMPORTS = {
    "YesCaptcha": "providers.captcha.yescaptcha",
    "TwoCaptcha": "providers.captcha.twocaptcha",
    "EzCaptcha": "providers.captcha.ezcaptcha",
    "CaptchaRunCaptcha": "providers.captcha.captcharun",
    "ManualCaptcha": "providers.captcha.manual",
    "LocalSolverCaptcha": "providers.captcha.local_solver",
}


def __getattr__(name: str):
    module_path = _LAZY_IMPORTS.get(name)
    if module_path is not None:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _definition_auth_fields(definition) -> list[str]:
    if not definition:
        return []
    return [
        str(field.get("key") or "")
        for field in definition.get_fields()
        if str(field.get("category") or "") == "auth" and str(field.get("key") or "")
    ]


def has_captcha_configured(provider_key: str, extra: dict | None = None) -> bool:
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository
    from infrastructure.provider_settings_repository import ProviderSettingsRepository

    key = str(provider_key or "").strip()
    if key == "manual":
        return True

    definition = ProviderDefinitionsRepository().get_by_key("captcha", key)
    if not definition or not definition.enabled:
        return False

    merged = ProviderSettingsRepository().resolve_runtime_settings("captcha", key, extra or {})
    auth_fields = _definition_auth_fields(definition)
    if not auth_fields:
        return True
    return any(str(merged.get(field_key, "")).strip() for field_key in auth_fields)


def create_captcha_solver(provider_key: str, extra: dict | None = None) -> BaseCaptcha:
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository
    from infrastructure.provider_settings_repository import ProviderSettingsRepository
    from providers.captcha.local_solver import LocalSolverCaptcha
    from providers.captcha.manual import ManualCaptcha
    from providers.captcha.twocaptcha import TwoCaptcha
    from providers.captcha.captcharun import CaptchaRunCaptcha
    from providers.captcha.ezcaptcha import EzCaptcha
    from providers.captcha.yescaptcha import YesCaptcha

    key = str(provider_key or "").strip().lower()
    if key == "manual":
        return ManualCaptcha()

    definition = ProviderDefinitionsRepository().get_by_key("captcha", key)
    if not definition or not definition.enabled:
        raise RuntimeError(f"验证码 provider 不存在或未启用: {key}")
    merged = ProviderSettingsRepository().resolve_runtime_settings("captcha", key, extra or {})
    driver_type = (definition.driver_type if definition else key).lower()

    if driver_type == "local_solver":
        return LocalSolverCaptcha(str(merged.get("solver_url", "") or ""))
    if driver_type == "yescaptcha_api":
        client_key = str(merged.get("yescaptcha_key", "") or "")
        if not client_key:
            raise RuntimeError("YesCaptcha Key 未配置，无法继续协议注册")
        api_host = str(merged.get("yescaptcha_api_host", "") or "")
        return YesCaptcha(client_key, api_host=api_host or "https://api.yescaptcha.com")
    if driver_type == "twocaptcha_api":
        api_key = str(merged.get("twocaptcha_key", "") or "")
        if not api_key:
            raise RuntimeError("2Captcha Key 未配置，无法继续协议注册")
        return TwoCaptcha(api_key)
    if driver_type == "ezcaptcha_api":
        client_key = str(merged.get("ezcaptcha_key", "") or "")
        if not client_key:
            raise RuntimeError("EZ-Captcha Key 未配置，无法继续协议注册")
        api_host = str(merged.get("ezcaptcha_api_host", "") or "")
        return EzCaptcha(client_key=client_key, api_host=api_host or "https://api.ez-captcha.com")
    if driver_type == "captcharun_api":
        api_key = str(merged.get("captcharun_api_key", "") or "")
        if not api_key:
            raise RuntimeError("CaptchaRun API Key 未配置，无法继续协议注册")
        api_host = str(merged.get("captcharun_api_host", "") or "")
        return CaptchaRunCaptcha(api_key=api_key, api_host=api_host or "https://api.captcha-run.com")
    raise ValueError(f"未知验证码解决器: {provider_key}")
