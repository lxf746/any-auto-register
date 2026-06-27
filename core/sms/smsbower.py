"""SMSBower provider — API compatible with HeroSMS, only base URL differs."""
from __future__ import annotations

import requests

from core.sms.herosms import HeroSmsProvider


class SmsBowerProvider(HeroSmsProvider):
    """SMSBower provider — API compatible with HeroSMS, only base URL differs."""

    BASE_URL = "https://smsbower.page/stubs/handler_api.php"

    def _request(self, params: dict, *, needs_key: bool = True, timeout: int = 30) -> requests.Response:
        payload = dict(params)
        if needs_key or self.api_key:
            payload["api_key"] = self.api_key
        resp = self._get_session().get(self.BASE_URL, params=payload, timeout=timeout)
        resp.raise_for_status()
        return resp
