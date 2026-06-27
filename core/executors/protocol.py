"""Pure protocol executor - based on curl_cffi"""
from curl_cffi import requests as curl_requests
from ..base_executor import BaseExecutor, Response
from ..mixins.managed_session import ManagedSession


class ProtocolExecutor(BaseExecutor, ManagedSession):
    def __init__(self, proxy: str = None, impersonate: str = "safari17_0"):
        super().__init__(proxy)
        self._impersonate = impersonate
        self._proxy = proxy
        # Session is now created lazily via ManagedSession._get_session()

    def _create_session(self):
        """Create a new curl_requests.Session with configured impersonate and proxy."""
        s = curl_requests.Session()
        s.impersonate = self._impersonate
        if self._proxy:
            s.proxies = {"http": self._proxy, "https": self._proxy}
        s.headers.update({
            "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36")
        })
        return s

    @property
    def s(self):
        """Backward-compatible session accessor."""
        return self._get_session()

    def _wrap(self, r) -> Response:
        cookies = {c.name: c.value for c in self.s.cookies.jar}
        return Response(
            status_code=r.status_code,
            text=r.text,
            headers=dict(r.headers),
            cookies=cookies,
        )

    def get(self, url, *, headers=None, params=None) -> Response:
        r = self.s.get(url, headers=headers, params=params)
        return self._wrap(r)

    def post(self, url, *, headers=None, params=None, data=None, json=None) -> Response:
        r = self.s.post(url, headers=headers, params=params, data=data, json=json)
        return self._wrap(r)

    def get_cookies(self) -> dict:
        return {c.name: c.value for c in self.s.cookies.jar}

    def set_cookies(self, cookies: dict) -> None:
        for k, v in cookies.items():
            self.s.cookies.set(k, v)

    def close(self) -> None:
        ManagedSession.close(self)
