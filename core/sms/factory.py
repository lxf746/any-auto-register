"""Factory function for creating SMS provider instances."""
from __future__ import annotations

from core.sms.base import SmsProvider
from core.sms.cache import (
    HERO_SMS_DEFAULT_COUNTRY,
    HERO_SMS_DEFAULT_SERVICE,
    _safe_bool,
    _safe_float,
    _safe_int,
)
from core.sms.herosms import HeroSmsProvider
from core.sms.sms_activate import SmsActivateProvider
from core.sms.smsbower import SmsBowerProvider


def create_sms_provider(provider_key: str, config: dict) -> SmsProvider:
    """Create an SMS provider instance from config."""
    if provider_key in ("sms_activate", "sms_activate_api"):
        api_key = config.get("sms_activate_api_key", "")
        if not api_key:
            raise RuntimeError("SMS-Activate API Key not configured")
        return SmsActivateProvider(
            api_key=api_key,
            default_country=config.get("sms_activate_country", config.get("sms_activate_default_country", "")),
            proxy=config.get("sms_proxy") or config.get("proxy") or None,
        )
    if provider_key in ("herosms", "herosms_api"):
        api_key = str(config.get("herosms_api_key", "") or "").strip()
        if not api_key:
            raise RuntimeError("HeroSMS API Key not configured")
        return HeroSmsProvider(
            api_key=api_key,
            default_service=str(config.get("sms_service") or config.get("herosms_service") or config.get("herosms_default_service") or HERO_SMS_DEFAULT_SERVICE),
            default_country=str(config.get("sms_country") or config.get("herosms_country") or config.get("herosms_default_country") or HERO_SMS_DEFAULT_COUNTRY),
            max_price=_safe_float(config.get("herosms_max_price"), -1),
            proxy=str(config.get("sms_proxy") or config.get("proxy") or "") or None,
            reuse_phone_to_max=_safe_bool(config.get("register_reuse_phone_to_max"), True),
            phone_success_max=max(0, _safe_int(config.get("register_phone_extra_max") or config.get("register_phone_success_max"), 3)),
        )
    if provider_key in ("smsbower", "smsbower_api"):
        api_key = str(config.get("smsbower_api_key", "") or "").strip()
        if not api_key:
            raise RuntimeError("SMSBower API Key not configured")
        return SmsBowerProvider(
            api_key=api_key,
            default_service=str(config.get("sms_service") or config.get("smsbower_service") or config.get("smsbower_default_service") or HERO_SMS_DEFAULT_SERVICE),
            default_country=str(config.get("sms_country") or config.get("smsbower_country") or config.get("smsbower_default_country") or HERO_SMS_DEFAULT_COUNTRY),
            max_price=_safe_float(config.get("smsbower_max_price"), -1),
            proxy=str(config.get("sms_proxy") or config.get("proxy") or "") or None,
            reuse_phone_to_max=_safe_bool(config.get("register_reuse_phone_to_max"), True),
            phone_success_max=max(0, _safe_int(config.get("register_phone_extra_max") or config.get("register_phone_success_max"), 3)),
        )
    raise RuntimeError(f"Unknown SMS provider: {provider_key}")
