"""SMS-Activate implementation (https://sms-activate.guru)."""
from __future__ import annotations

import logging
import time

import requests

from core.sms.base import SmsActivation, SmsProvider

logger = logging.getLogger(__name__)

# Delay between SMS status polling retries (seconds)
SMS_POLL_RETRY_DELAY = 3

SMS_ACTIVATE_SERVICES = {
    "cursor": "ot",
    "chatgpt": "dr",
    "openai": "dr",
    "google": "go",
    "microsoft": "mg",
    "default": "ot",
}

SMS_ACTIVATE_COUNTRIES = {
    "ru": "0",
    "us": "187",
    "uk": "16",
    "in": "22",
    "id": "6",
    "ph": "4",
    "th": "52",
    "br": "73",
    "default": "0",
}


def _resolve_sms_activate_country_id(country: str, default_country: str) -> str:
    raw = str(country or default_country or "").strip().lower()
    if not raw:
        raw = "default"
    if raw.isdigit():
        return raw
    return SMS_ACTIVATE_COUNTRIES.get(raw, SMS_ACTIVATE_COUNTRIES["default"])


class SmsActivateProvider(SmsProvider):
    """SMS-Activate (sms-activate.guru) provider."""

    BASE_URL = "https://api.sms-activate.guru/stubs/handler_api.php"

    def __init__(self, api_key: str, *, default_country: str = "", proxy: str = None):
        self.api_key = api_key
        self.default_country = default_country or "ru"
        self._proxy = {"http": proxy, "https": proxy} if proxy else None
        self._session = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            s = requests.Session()
            s.proxies = self._proxy or {}
            self._session = s
        return self._session

    def _request(self, action: str, **params) -> str:
        params["api_key"] = self.api_key
        params["action"] = action
        resp = self._get_session().get(
            self.BASE_URL,
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        return resp.text.strip()

    def close(self):
        if self._session:
            self._session.close()
            self._session = None

    def get_balance(self) -> float:
        result = self._request("getBalance")
        if result.startswith("ACCESS_BALANCE:"):
            return float(result.split(":")[1])
        raise RuntimeError(f"SMS-Activate getBalance failed: {result}")

    def get_number(self, *, service: str, country: str = "") -> SmsActivation:
        service_code = SMS_ACTIVATE_SERVICES.get(service, SMS_ACTIVATE_SERVICES["default"])
        country_id = _resolve_sms_activate_country_id(country, self.default_country)

        result = self._request("getNumber", service=service_code, country=country_id)
        if result.startswith("ACCESS_NUMBER:"):
            parts = result.split(":")
            return SmsActivation(
                activation_id=parts[1],
                phone_number=parts[2],
                country=country or self.default_country,
            )

        if "NO_NUMBERS" in result:
            raise RuntimeError(f"SMS-Activate: no numbers available (service={service_code}, country={country_id})")
        if "NO_BALANCE" in result:
            raise RuntimeError("SMS-Activate: insufficient balance")
        raise RuntimeError(f"SMS-Activate getNumber failed: {result}")

    def get_code(self, activation_id: str, *, timeout: int = 120) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self._request("getStatus", id=activation_id)
            if result.startswith("STATUS_OK:"):
                return result.split(":")[1]
            if result == "STATUS_WAIT_CODE":
                time.sleep(SMS_POLL_RETRY_DELAY)
                continue
            if result == "STATUS_WAIT_RETRY":
                self._request("setStatus", id=activation_id, status="6")
                time.sleep(SMS_POLL_RETRY_DELAY)
                continue
            if result == "STATUS_CANCEL":
                return ""
            time.sleep(SMS_POLL_RETRY_DELAY)

        self.cancel(activation_id)
        return ""

    def cancel(self, activation_id: str) -> bool:
        result = self._request("setStatus", id=activation_id, status="8")
        return "ACCESS" in result

    def report_success(self, activation_id: str) -> bool:
        result = self._request("setStatus", id=activation_id, status="6")
        return "ACCESS" in result
