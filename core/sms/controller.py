"""PhoneCallbackController — callable adapter for browser registration."""
from __future__ import annotations

import logging
from typing import Callable, Optional

from core.rate_limiter import check_provider_limit, rate_limit_metrics
from core.sms.base import SmsActivation, SmsProvider
from core.sms.cache import (
    HERO_SMS_DEFAULT_COUNTRY,
    HERO_SMS_DEFAULT_SERVICE,
    _HERO_SMS_VERIFY_LOCK,
    _safe_bool,
    _safe_float,
    _safe_int,
)
from core.sms.factory import create_sms_provider
from core.sms.herosms import HeroSmsProvider

logger = logging.getLogger(__name__)


class PhoneCallbackController:
    """Callable phone callback with optional lifecycle hooks for advanced providers."""

    def __init__(self, provider_key: str, config: dict, *, service: str, country: str = "", log_fn=None):
        self.provider_key = provider_key
        self.config = dict(config or {})
        self.service = service
        self.country = country
        self.log = log_fn or logger.info
        self.provider: Optional[SmsProvider] = None
        self.activation: Optional[SmsActivation] = None
        self.phase = "need_number"
        self.completed = False
        self._verify_lock_acquired = False
        self.awaiting_external_success = False

    def _provider(self) -> SmsProvider:
        if self.provider is None:
            if not check_provider_limit("sms", self.provider_key, metrics=rate_limit_metrics):
                raise RuntimeError(f"Rate limit exceeded for SMS provider {self.provider_key}")
            self.provider = create_sms_provider(self.provider_key, self.config)
        return self.provider

    def __call__(self) -> str:
        provider = self._provider()
        if self.phase == "need_number":
            if self.provider_key == "herosms" and not self._verify_lock_acquired:
                _HERO_SMS_VERIFY_LOCK.acquire()
                self._verify_lock_acquired = True

            try:
                effective_country = self.country
                auto_select = _safe_bool(self.config.get("herosms_auto_country") or self.config.get("smsbower_auto_country"), False)
                if auto_select and isinstance(provider, HeroSmsProvider):
                    self.log("Querying best country (lowest price + sufficient stock)...")
                    try:
                        min_stock = _safe_int(self.config.get("herosms_auto_country_min_stock") or self.config.get("smsbower_auto_country_min_stock"), 20)
                        max_price_limit = _safe_float(self.config.get("herosms_auto_country_max_price") or self.config.get("smsbower_auto_country_max_price"), 0)
                        best = provider.get_best_country(
                            service=self.service,
                            min_stock=min_stock,
                            max_price=max_price_limit,
                        )
                        if best:
                            self.log(f"Auto-selected best country: {best}")
                            effective_country = best
                        else:
                            self.log("No country meeting the criteria found, using default configuration")
                    except Exception as exc:
                        self.log(f"Smart country selection failed ({exc}), using default configuration")

                country_label = effective_country or self.config.get("sms_country") or self.config.get("sms_activate_country") or "default"
                self.log(f"Entered add_phone, preparing to rent phone number: provider={self.provider_key} service={self.service} country={country_label}")
                self.log(f"Getting phone number from {self.provider_key}...")
                try:
                    self.activation = provider.get_number(service=self.service, country=effective_country)
                except Exception as first_exc:
                    fallback_country = self.country or self.config.get("sms_country") or self.config.get("herosms_country") or ""
                    if auto_select and effective_country != fallback_country and fallback_country:
                        self.log(f"Auto-selected country ({effective_country}) failed to get number, falling back to default country ({fallback_country})...")
                        try:
                            self.activation = provider.get_number(service=self.service, country=fallback_country)
                        except Exception:
                            if self._verify_lock_acquired:
                                _HERO_SMS_VERIFY_LOCK.release()
                                self._verify_lock_acquired = False
                            raise
                    else:
                        if self._verify_lock_acquired:
                            _HERO_SMS_VERIFY_LOCK.release()
                            self._verify_lock_acquired = False
                        raise
                self.phase = "need_code"
                reused = bool((self.activation.metadata or {}).get("reused"))
                reuse_label = "reused number" if reused else "new number"
                self.log(f"Successfully rented number ({reuse_label}): {self.activation.phone_number} (activation_id={self.activation.activation_id})")
                return self.activation.phone_number
            except Exception:
                if self._verify_lock_acquired:
                    _HERO_SMS_VERIFY_LOCK.release()
                    self._verify_lock_acquired = False
                raise

        if self.phase == "need_code" and self.activation:
            self.log(f"Waiting for SMS verification code... (activation_id={self.activation.activation_id})")
            code = provider.get_code(self.activation.activation_id, timeout=180)
            if code:
                self.log(f"Received verification code: {code}")
                if getattr(provider, "auto_report_success_on_code", True):
                    self.report_success()
                else:
                    self.awaiting_external_success = True
            else:
                self.log(f"⚠️ No verification code received: activation_id={self.activation.activation_id}")
            return code
        return ""

    def set_resend_callback(self, callback: Callable[[], None] | None) -> None:
        if self.provider is not None:
            self.provider.set_resend_callback(callback)
        else:
            original_provider = self._provider()
            original_provider.set_resend_callback(callback)

    def mark_code_failed(self, reason: str = "") -> None:
        if self.activation and self.provider:
            hook = getattr(self.provider, "mark_code_failed", None)
            if callable(hook):
                hook(self.activation.activation_id, reason=reason)
            self.phase = "need_code"
            self.awaiting_external_success = False

    def mark_send_failed(self, reason: str = "") -> None:
        if self.activation and self.provider:
            hook = getattr(self.provider, "mark_send_failed", None)
            if callable(hook):
                hook(self.activation.activation_id, reason=reason)
            self.awaiting_external_success = False

    def mark_send_succeeded(self) -> None:
        if self.activation and self.provider:
            hook = getattr(self.provider, "mark_send_succeeded", None)
            if callable(hook):
                hook(self.activation.activation_id)

    def report_success(self) -> None:
        if self.activation and self.provider and not self.completed:
            self.provider.report_success(self.activation.activation_id)
            self.completed = True
            self.phase = "done"
            self.awaiting_external_success = False
            self.log(f"SMS verification successful, marked number as completed: activation_id={self.activation.activation_id}")
        if self._verify_lock_acquired:
            _HERO_SMS_VERIFY_LOCK.release()
            self._verify_lock_acquired = False

    def cleanup(self) -> None:
        if self.activation and not self.completed:
            try:
                provider = self._provider()
                if self.awaiting_external_success and not getattr(provider, "auto_report_success_on_code", True):
                    self.report_success()
                else:
                    provider.cancel(self.activation.activation_id)
                    self.log(f"Released unused number: activation_id={self.activation.activation_id}")
            except Exception:
                pass
        if self._verify_lock_acquired:
            _HERO_SMS_VERIFY_LOCK.release()
            self._verify_lock_acquired = False


def create_phone_callbacks(
    provider_key: str,
    config: dict,
    *,
    service: str,
    country: str = "",
    log_fn=None,
) -> tuple:
    """Create (phone_callback, cleanup) tuple for browser registration."""
    controller = PhoneCallbackController(
        provider_key,
        config,
        service=service,
        country=country,
        log_fn=log_fn,
    )
    return controller, controller.cleanup
