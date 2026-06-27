"""HeroSMS implementation (https://hero-sms.com/stubs/handler_api.php)."""
from __future__ import annotations

import json
import logging
import time
from typing import Callable

import requests

from core.sms.base import SmsActivation, SmsProvider
from core.sms.cache import (
    HERO_SMS_DEFAULT_COUNTRY,
    HERO_SMS_DEFAULT_SERVICE,
    HERO_SMS_PHONE_LIFETIME,
    _HERO_SMS_CACHE,
    _HERO_SMS_CACHE_LOCK,
    _HERO_SMS_VERIFY_LOCK,
    _candidate_is_attempted,
    _hash_secret,
    _has_real_sms_time,
    _make_sms_candidate,
    _normalize_hero_proxy,
    _parse_hero_status_text,
    hero_sms_cache_file,
)

logger = logging.getLogger(__name__)


class HeroSmsProvider(SmsProvider):
    """HeroSMS provider with resend, SMS event dedupe, and short-lived phone reuse."""

    BASE_URL = "https://hero-sms.com/stubs/handler_api.php"
    auto_report_success_on_code = False

    def __init__(
        self,
        api_key: str,
        *,
        default_service: str = HERO_SMS_DEFAULT_SERVICE,
        default_country: str = HERO_SMS_DEFAULT_COUNTRY,
        max_price: float = -1,
        proxy: str | None = None,
        reuse_phone_to_max: bool = True,
        phone_success_max: int = 3,
    ):
        self.api_key = str(api_key or "").strip()
        self.default_service = str(default_service or HERO_SMS_DEFAULT_SERVICE).strip()
        self.default_country = str(default_country or HERO_SMS_DEFAULT_COUNTRY).strip()
        self.max_price = float(max_price or -1)
        self.proxy = _normalize_hero_proxy(proxy)
        self.proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        self.reuse_phone_to_max = bool(reuse_phone_to_max)
        self.phone_success_max = max(0, int(phone_success_max or 0))
        self.openai_resend_callback: Callable[[], None] | None = None
        self.last_code_result: dict | None = None
        self.current_activation: SmsActivation | None = None
        self._session = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            s = requests.Session()
            s.proxies = self.proxies or {}
            self._session = s
        return self._session

    def close(self):
        if self._session:
            self._session.close()
            self._session = None

    def _request(self, params: dict, *, needs_key: bool = True, timeout: int = 30) -> requests.Response:
        payload = dict(params)
        if needs_key:
            payload["api_key"] = self.api_key
        resp = self._get_session().get(self.BASE_URL, params=payload, timeout=timeout)
        resp.raise_for_status()
        return resp

    def get_balance(self) -> float:
        text = self._request({"action": "getBalance"}).text.strip()
        if text.startswith("ACCESS_BALANCE:"):
            return float(text.split(":", 1)[1])
        raise RuntimeError(f"HeroSMS getBalance failed: {text}")

    def get_services(self, country: str | int | None = None, lang: str = "cn") -> list:
        params = {"action": "getServicesList", "lang": lang}
        if country not in (None, ""):
            params["country"] = country
        data = self._request(params, needs_key=False).json()
        if isinstance(data, dict) and data.get("status") == "success":
            return list(data.get("services") or [])
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            result = []
            for key, value in data.items():
                if key in ("status", "message", "error"):
                    continue
                if isinstance(value, dict):
                    if "code" not in value:
                        value["code"] = key
                    result.append(value)
                elif isinstance(value, str):
                    result.append({"code": key, "name": value})
            if result:
                return result
        raise RuntimeError("HeroSMS getServicesList returned unexpected response")

    def get_countries(self) -> list:
        data = self._request({"action": "getCountries"}, needs_key=False).json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if data.get("status") == 0 or data.get("message") == "No access":
                raise RuntimeError(f"SMS API access denied: {data.get('message', 'unknown')}")
            result = []
            for key, value in data.items():
                if key in ("status", "message", "data", "error"):
                    continue
                if isinstance(value, dict):
                    if "id" not in value:
                        value["id"] = key
                    result.append(value)
                elif isinstance(value, str):
                    result.append({"id": key, "eng": value, "name": value})
            if result:
                return result
        raise RuntimeError("SMS getCountries returned unexpected response")

    def get_prices(self, service: str | None = None, country: str | int | None = None) -> dict:
        params = {"action": "getPrices"}
        if service:
            params["service"] = service
        if country not in (None, ""):
            params["country"] = country
        data = self._request(params).json()
        if isinstance(data, dict):
            return data
        raise RuntimeError("HeroSMS getPrices returned unexpected response")

    def get_top_countries(self, service: str | None = None) -> list[dict]:
        service_code = str(service or self.default_service or HERO_SMS_DEFAULT_SERVICE).strip()

        for action in ("getTopCountriesByServiceRank", "getTopCountriesByService"):
            try:
                data = self._request({"action": action, "service": service_code}).json()
                rows = self._parse_top_countries_response(data)
                if rows:
                    rows.sort(key=lambda r: (r.get("price") or 999, -(r.get("count") or 0)))
                    return rows
            except Exception:
                continue

        try:
            prices = self.get_prices(service=service_code)
            rows = []
            for country_id, services in prices.items():
                if not isinstance(services, dict):
                    continue
                svc_data = services.get(service_code)
                if not isinstance(svc_data, dict):
                    continue
                price = svc_data.get("cost") or svc_data.get("price")
                count = svc_data.get("count") or svc_data.get("qty") or svc_data.get("available")
                try:
                    price = float(price) if price is not None else None
                except (TypeError, ValueError):
                    price = None
                try:
                    count = int(count) if count is not None else 0
                except (TypeError, ValueError):
                    count = 0
                if price is not None and count > 0:
                    rows.append({"country": str(country_id), "price": price, "count": count})
            rows.sort(key=lambda r: (r.get("price") or 999, -(r.get("count") or 0)))
            return rows
        except Exception:
            return []

    def _parse_top_countries_response(self, data) -> list[dict]:
        rows = []
        items = data
        if isinstance(data, dict):
            items = data.get("data") or data.get("result") or data.get("response") or data
        if isinstance(items, dict):
            for key, value in items.items():
                if not isinstance(value, dict):
                    continue
                try:
                    country_id = str(int(key))
                except (TypeError, ValueError):
                    continue
                price = value.get("price") or value.get("cost") or value.get("retail_price")
                count = value.get("count") or value.get("qty") or value.get("available") or value.get("stock")
                name = value.get("name") or value.get("countryName") or value.get("country_name") or ""
                try:
                    price = float(price) if price is not None else None
                except (TypeError, ValueError):
                    price = None
                try:
                    count = int(count) if count is not None else 0
                except (TypeError, ValueError):
                    count = 0
                if price is not None:
                    rows.append({"country": country_id, "name": str(name), "price": price, "count": count})
        elif isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                country_id = item.get("country") or item.get("countryId") or item.get("country_id") or item.get("id")
                if country_id is None:
                    continue
                price = item.get("price") or item.get("cost") or item.get("retail_price") or item.get("retailPrice")
                count = item.get("count") or item.get("qty") or item.get("available") or item.get("stock") or item.get("total")
                name = item.get("name") or item.get("countryName") or item.get("country_name") or item.get("title") or ""
                try:
                    price = float(price) if price is not None else None
                except (TypeError, ValueError):
                    price = None
                try:
                    count = int(count) if count is not None else 0
                except (TypeError, ValueError):
                    count = 0
                if price is not None:
                    rows.append({"country": str(country_id), "name": str(name), "price": price, "count": count})
        return rows

    def get_best_country(self, service: str | None = None, *, min_stock: int = 20, max_price: float = 0) -> str | None:
        ALLOWED_COUNTRIES = {
            "52",   # Thailand (verified to use SMS)
        }

        try:
            rows = self.get_top_countries(service=service)
        except Exception as exc:
            logger.warning("get_best_country query failed: %s", exc)
            return None

        if not rows:
            return None

        for row in rows:
            country_id = str(row.get("country") or "")
            if country_id not in ALLOWED_COUNTRIES:
                continue
            price = row.get("price") or 0
            count = row.get("count") or 0
            if count < min_stock:
                continue
            if max_price > 0 and price > max_price:
                continue
            return country_id

        for row in rows:
            country_id = str(row.get("country") or "")
            if country_id not in ALLOWED_COUNTRIES:
                continue
            price = row.get("price") or 0
            count = row.get("count") or 0
            if count <= 0:
                continue
            if max_price > 0 and price > max_price:
                continue
            return country_id

        return None

    def _cache_identity(self, service: str, country: str) -> dict:
        return {
            "api_key_hash": _hash_secret(self.api_key),
            "service": str(service),
            "country": str(country),
        }

    def _load_cache(self, service: str, country: str) -> dict | None:
        import core.sms.cache as _cache_mod
        global_cache = _cache_mod._HERO_SMS_CACHE
        if global_cache is not None:
            cache = global_cache
        else:
            path = hero_sms_cache_file()
            if not path.exists():
                return None
            try:
                cache = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return None
        identity = self._cache_identity(service, country)
        if any(str(cache.get(key) or "") != str(value) for key, value in identity.items()):
            return None
        elapsed = time.time() - float(cache.get("acquired_at") or 0)
        if elapsed >= HERO_SMS_PHONE_LIFETIME or cache.get("reuse_stopped"):
            self._clear_cache()
            return None
        if self.phone_success_max > 0 and int(cache.get("use_count") or 0) >= self.phone_success_max:
            cache["reuse_stopped"] = True
            cache["stop_reason"] = f"success max reached ({self.phone_success_max})"
            self._save_cache(cache)
            return None
        cache["used_codes"] = set(cache.get("used_codes") or [])
        cache["attempted_sms_keys"] = set(cache.get("attempted_sms_keys") or [])
        _cache_mod._HERO_SMS_CACHE = cache
        return cache

    def _save_cache(self, cache: dict | None) -> None:
        import core.sms.cache as _cache_mod
        _cache_mod._HERO_SMS_CACHE = cache
        path = hero_sms_cache_file()
        if cache is None:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return
        serializable = dict(cache)
        serializable["used_codes"] = sorted(serializable.get("used_codes") or [])
        serializable["attempted_sms_keys"] = sorted(serializable.get("attempted_sms_keys") or [])
        serializable.pop("client", None)
        path.write_text(json.dumps(serializable, ensure_ascii=False), encoding="utf-8")

    def _clear_cache(self) -> None:
        self._save_cache(None)

    def _stop_reuse(self, reason: str) -> None:
        import core.sms.cache as _cache_mod
        with _HERO_SMS_CACHE_LOCK:
            cache = _cache_mod._HERO_SMS_CACHE
            if not cache:
                return
            cache["reuse_stopped"] = True
            cache["stop_reason"] = reason
            self._save_cache(cache)

    def _request_number_raw(self, service: str, country: str) -> dict:
        common = {"service": service, "country": country}

        effective_max_price = self.max_price if self.max_price > 0 else 1
        try:
            prices = self.get_prices(service=service, country=country)
            country_prices = prices.get(str(country)) or prices.get(country) or {}
            service_prices = country_prices.get(service) or {}
            actual_cost = service_prices.get("cost") or service_prices.get("price")
            if actual_cost is not None:
                actual_cost = float(actual_cost)
                dynamic_max = round(actual_cost * 3, 4)
                if self.max_price > 0:
                    effective_max_price = min(self.max_price, max(dynamic_max, 0.2))
                else:
                    effective_max_price = max(dynamic_max, 0.2)
        except Exception:
            pass

        common["maxPrice"] = effective_max_price

        v2_error = ""
        try:
            resp = self._request({"action": "getNumberV2", **common})
            try:
                data = resp.json()
            except ValueError:
                data = None
            if isinstance(data, dict) and data.get("activationId"):
                return data
            v2_error = resp.text.strip()[:200]
        except Exception as exc:
            v2_error = str(exc)

        if "NO_NUMBERS" in v2_error and self.max_price > 0 and effective_max_price < self.max_price:
            common["maxPrice"] = self.max_price
            try:
                resp = self._request({"action": "getNumberV2", **common})
                try:
                    data = resp.json()
                except ValueError:
                    data = None
                if isinstance(data, dict) and data.get("activationId"):
                    return data
                v2_error = resp.text.strip()[:200]
            except Exception as exc:
                v2_error = str(exc)

        try:
            text = self._request({"action": "getNumber", **common}).text.strip()
            if text.startswith("ACCESS_NUMBER:"):
                parts = text.split(":", 2)
                if len(parts) == 3:
                    return {
                        "activationId": parts[1],
                        "phoneNumber": parts[2],
                        "countryPhoneCode": "",
                        "activationCost": None,
                    }
            raise RuntimeError(text[:200])
        except Exception as exc:
            raise RuntimeError(f"HeroSMS failed to get number: V2={v2_error}; V1={exc}") from exc

    @staticmethod
    def _format_phone(number_info: dict) -> str:
        raw = str(number_info.get("phoneNumber") or "").strip()
        country_phone_code = str(number_info.get("countryPhoneCode") or "").strip()
        if raw.startswith("+"):
            return raw
        if country_phone_code and raw.startswith(country_phone_code):
            return f"+{raw}"
        if country_phone_code:
            return f"+{country_phone_code}{raw}"
        return f"+{raw}"

    def get_number(self, *, service: str, country: str = "") -> SmsActivation:
        service_code = str(self.default_service or service or HERO_SMS_DEFAULT_SERVICE).strip()
        country_id = str(country or self.default_country or HERO_SMS_DEFAULT_COUNTRY).strip()
        with _HERO_SMS_VERIFY_LOCK:
            with _HERO_SMS_CACHE_LOCK:
                cache = self._load_cache(service_code, country_id) if self.reuse_phone_to_max else None
                if cache:
                    activation = SmsActivation(
                        activation_id=str(cache["activation_id"]),
                        phone_number=str(cache["phone_number"]),
                        country=country_id,
                        metadata={"reused": True, "use_count": int(cache.get("use_count") or 0)},
                    )
                    self.current_activation = activation
                    return activation

                number_info = self._request_number_raw(service_code, country_id)
                activation_id = str(number_info.get("activationId") or "")
                phone = self._format_phone(number_info)
                if not activation_id or not phone.strip("+"):
                    raise RuntimeError("HeroSMS returned incomplete number information")
                cache = {
                    **self._cache_identity(service_code, country_id),
                    "activation_id": activation_id,
                    "phone_number": phone,
                    "acquired_at": time.time(),
                    "use_count": 0,
                    "used_codes": set(),
                    "attempted_sms_keys": set(),
                    "reuse_stopped": False,
                    "stop_reason": "",
                }
                self._save_cache(cache)
                activation = SmsActivation(
                    activation_id=activation_id,
                    phone_number=phone,
                    country=country_id,
                    metadata={"reused": False, "number_info": number_info},
                )
                self.current_activation = activation
                return activation

    def get_status(self, activation_id: str) -> dict:
        return _parse_hero_status_text(self._request({"action": "getStatus", "id": activation_id}).text)

    def get_status_v2(self, activation_id: str) -> dict:
        resp = self._request({"action": "getStatusV2", "id": activation_id})
        text = resp.text.strip()
        try:
            data = resp.json()
        except ValueError:
            return _parse_hero_status_text(text)
        if isinstance(data, str):
            return _parse_hero_status_text(data)
        if not isinstance(data, dict):
            return {"status": "unknown", "raw": data}
        raw_status = data.get("status")
        if isinstance(raw_status, str):
            parsed = _parse_hero_status_text(raw_status)
            if parsed.get("status") != "unknown":
                return parsed
        for channel in ("sms", "call"):
            item = data.get(channel)
            if isinstance(item, dict):
                candidate = _make_sms_candidate(
                    activation_id,
                    f"getStatusV2.{channel}",
                    item.get("code"),
                    {
                        "channel": channel,
                        "dateTime": item.get("dateTime"),
                        "text": item.get("text"),
                        "from": item.get("from"),
                        "url": item.get("url"),
                        "verificationType": data.get("verificationType"),
                    },
                )
                if candidate:
                    return candidate
        return {"status": "wait_code", "raw": data}

    def get_active_activations(self, start: int = 0, limit: int = 20) -> list:
        data = self._request({"action": "getActiveActivations", "start": start, "limit": limit}).json()
        if isinstance(data, dict) and "data" in data:
            return list(data.get("data") or [])
        return []

    def set_status(self, activation_id: str, status: int) -> str:
        return self._request({"action": "setStatus", "id": activation_id, "status": status}).text.strip()

    def cancel_activation(self, activation_id: str) -> bool:
        try:
            resp = self._request({"action": "cancelActivation", "id": activation_id})
            if resp.status_code == 204 or "ACCESS_CANCEL" in resp.text:
                return True
        except Exception:
            pass
        try:
            return "ACCESS_CANCEL" in self.set_status(activation_id, 8)
        except Exception:
            return False

    def finish_activation(self, activation_id: str) -> bool:
        try:
            resp = self._request({"action": "finishActivation", "id": activation_id})
            text = resp.text.strip()
            return resp.status_code in (200, 204) or "ACCESS" in text
        except Exception:
            try:
                return "ACCESS" in self.set_status(activation_id, 6)
            except Exception:
                return False

    def request_resend_sms(self, activation_id: str) -> bool:
        try:
            self.set_status(activation_id, 3)
            return True
        except Exception:
            return False

    def wait_for_code(self, activation_id: str, *, timeout: int = 180, poll_interval: int = 3) -> dict | None:
        import core.sms.cache as _cache_mod
        deadline = time.time() + timeout
        start = time.time()
        last_hero_resend = start
        openai_resent = False
        warned_v2 = False
        while time.time() < deadline:
            with _HERO_SMS_CACHE_LOCK:
                cache = _cache_mod._HERO_SMS_CACHE or {}
                used_codes = set(cache.get("used_codes") or [])
                attempted_sms_keys = set(cache.get("attempted_sms_keys") or [])

            for source in ("v2", "v1", "active"):
                try:
                    candidate = None
                    if source == "v2":
                        result = self.get_status_v2(activation_id)
                        if result.get("status") == "cancel":
                            return None
                        if result.get("status") == "ok":
                            candidate = result
                    elif source == "v1":
                        result = self.get_status(activation_id)
                        if result.get("status") == "cancel":
                            return None
                        if result.get("status") == "ok":
                            candidate = _make_sms_candidate(activation_id, "getStatus", result.get("code"))
                    else:
                        for item in self.get_active_activations():
                            if str(item.get("activationId")) == str(activation_id):
                                candidate = _make_sms_candidate(
                                    activation_id,
                                    "getActiveActivations",
                                    item.get("smsCode"),
                                    {
                                        "channel": "sms",
                                        "smsText": item.get("smsText"),
                                        "activationStatus": item.get("activationStatus"),
                                        "repeated": item.get("repeated"),
                                        "dateTime": item.get("dateTime"),
                                        "date": item.get("date") or item.get("smsDate") or item.get("smsTime"),
                                    },
                                )
                                break
                    if candidate and not _candidate_is_attempted(candidate, used_codes, attempted_sms_keys):
                        return candidate
                except Exception as exc:
                    if source == "v2" and not warned_v2:
                        logger.warning("HeroSMS getStatusV2 failed: %s", exc)
                        warned_v2 = True
                    else:
                        logger.debug("HeroSMS status check failed via %s: %s", source, exc)

            elapsed = time.time() - start
            if not openai_resent and elapsed >= 90 and self.openai_resend_callback:
                try:
                    self.openai_resend_callback()
                except Exception as exc:
                    logger.warning("OpenAI phone resend callback failed: %s", exc)
                self.request_resend_sms(activation_id)
                last_hero_resend = time.time()
                openai_resent = True
            elif time.time() - last_hero_resend >= 30:
                self.request_resend_sms(activation_id)
                last_hero_resend = time.time()

            time.sleep(poll_interval)
        return None

    def get_code(self, activation_id: str, *, timeout: int = 120) -> str:
        import core.sms.cache as _cache_mod
        wait_timeout = timeout
        with _HERO_SMS_CACHE_LOCK:
            cache = _cache_mod._HERO_SMS_CACHE or {}
            if cache and str(cache.get("activation_id")) == str(activation_id):
                remaining = int(HERO_SMS_PHONE_LIFETIME - (time.time() - float(cache.get("acquired_at") or 0)))
                wait_timeout = max(timeout, remaining, 60)
        candidate = self.wait_for_code(activation_id, timeout=wait_timeout)
        self.last_code_result = candidate
        return str((candidate or {}).get("code") or "")

    def cancel(self, activation_id: str) -> bool:
        import core.sms.cache as _cache_mod
        try:
            return self.cancel_activation(activation_id)
        finally:
            with _HERO_SMS_CACHE_LOCK:
                cache = _cache_mod._HERO_SMS_CACHE
                if cache and str(cache.get("activation_id")) == str(activation_id):
                    self._clear_cache()

    def report_success(self, activation_id: str) -> bool:
        import core.sms.cache as _cache_mod
        should_finish = False
        should_clear_cache = False
        handled_cached_activation = False
        with _HERO_SMS_CACHE_LOCK:
            cache = _cache_mod._HERO_SMS_CACHE
            if cache and str(cache.get("activation_id")) == str(activation_id):
                handled_cached_activation = True
                cache["use_count"] = int(cache.get("use_count") or 0) + 1
                self._record_last_attempt(cache, failed=False)
                remaining = HERO_SMS_PHONE_LIFETIME - (time.time() - float(cache.get("acquired_at") or 0))
                if not self.reuse_phone_to_max:
                    cache["reuse_stopped"] = True
                    cache["stop_reason"] = "reuse disabled"
                    should_finish = True
                    should_clear_cache = True
                elif self.phone_success_max > 0 and int(cache["use_count"]) >= self.phone_success_max:
                    cache["reuse_stopped"] = True
                    cache["stop_reason"] = f"success max reached ({self.phone_success_max})"
                    should_finish = True
                elif remaining <= 30:
                    cache["reuse_stopped"] = True
                    cache["stop_reason"] = "phone lifetime nearly expired"
                    should_finish = True
                    should_clear_cache = True
                self._save_cache(cache)
                if should_clear_cache:
                    self._clear_cache()
        if handled_cached_activation:
            if should_finish:
                self.finish_activation(activation_id)
            return True
        return self.finish_activation(activation_id)

    def _record_last_attempt(self, cache: dict, *, failed: bool) -> None:
        candidate = self.last_code_result or {}
        code = str(candidate.get("code") or "")
        sms_key = str(candidate.get("sms_key") or "")
        used_codes = set(cache.get("used_codes") or [])
        attempted_sms_keys = set(cache.get("attempted_sms_keys") or [])
        if code:
            used_codes.add(code)
        if sms_key:
            attempted_sms_keys.add(sms_key)
        cache["used_codes"] = used_codes
        cache["attempted_sms_keys"] = attempted_sms_keys
        if failed:
            cache["last_failed_reason"] = "invalid otp"

    def mark_code_failed(self, activation_id: str, reason: str = "") -> None:
        import core.sms.cache as _cache_mod
        with _HERO_SMS_CACHE_LOCK:
            cache = _cache_mod._HERO_SMS_CACHE
            if cache and str(cache.get("activation_id")) == str(activation_id):
                self._record_last_attempt(cache, failed=True)
                self._save_cache(cache)
        if self.openai_resend_callback:
            try:
                self.openai_resend_callback()
            except Exception:
                pass
        self.request_resend_sms(activation_id)

    def mark_send_succeeded(self, activation_id: str) -> None:
        try:
            self.set_status(activation_id, 1)
        except Exception:
            pass

    def mark_send_failed(self, activation_id: str, reason: str = "") -> None:
        reason_text = str(reason or "").lower()
        if any(keyword in reason_text for keyword in ("limit", "already", "too many", "exceeded", "maximum", "reached")):
            self._stop_reuse("phone limit reached")
        else:
            self._stop_reuse(reason or "phone rejected")

    def set_resend_callback(self, callback: Callable[[], None] | None) -> None:
        self.openai_resend_callback = callback

    def get_reuse_info(self) -> dict:
        import core.sms.cache as _cache_mod
        with _HERO_SMS_CACHE_LOCK:
            cache = _cache_mod._HERO_SMS_CACHE or self._load_cache(self.default_service, self.default_country) or {}
            if not cache:
                return {"alive": False}
            remaining = max(0, int(HERO_SMS_PHONE_LIFETIME - (time.time() - float(cache.get("acquired_at") or 0))))
            return {
                "alive": remaining > 0 and not bool(cache.get("reuse_stopped")),
                "phone_number": cache.get("phone_number", ""),
                "use_count": int(cache.get("use_count") or 0),
                "remaining_seconds": remaining,
                "reuse_stopped": bool(cache.get("reuse_stopped")),
                "stop_reason": cache.get("stop_reason", ""),
            }


def is_herosms_phone_cache_alive(config: dict | None = None) -> tuple[bool, dict]:
    """Return whether the current HeroSMS cache is reusable for scheduling."""
    from core.sms.cache import _safe_int
    config = dict(config or {})
    api_key = str(config.get("herosms_api_key") or "").strip()
    if not api_key:
        return False, {"alive": False}
    provider = HeroSmsProvider(
        api_key,
        default_service=str(config.get("sms_service") or HERO_SMS_DEFAULT_SERVICE),
        default_country=str(config.get("sms_country") or config.get("herosms_country") or HERO_SMS_DEFAULT_COUNTRY),
        phone_success_max=max(0, _safe_int(config.get("register_phone_success_max"), 3)),
    )
    info = provider.get_reuse_info()
    return bool(info.get("alive")), info
