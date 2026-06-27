"""Generic HTTP client - based on curl_cffi, supports proxy, retry, and session management"""
"""
HTTP client wrapper
HTTP request wrapper based on curl_cffi, supports proxy and error handling
"""

import time
import json
from typing import Optional, Dict, Any, Union, Tuple
from dataclasses import dataclass
import logging

from curl_cffi import requests as cffi_requests
from curl_cffi.requests import Session, Response

from core.mixins.managed_session import ManagedSession





logger = logging.getLogger(__name__)


@dataclass
class RequestConfig:
    """HTTP request configuration"""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    impersonate: str = "chrome136"
    verify_ssl: bool = True
    follow_redirects: bool = True


class HTTPClientError(Exception):
    """HTTP client exception"""
    pass


class HTTPClient(ManagedSession):
    """
    HTTP client wrapper
    Supports proxy, retry, error handling, and session management
    """

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        config: Optional[RequestConfig] = None,
        session: Optional[Session] = None
    ):
        """
        Initialize HTTP client

        Args:
            proxy_url: Proxy URL, e.g., "http://127.0.0.1:7890"
            config: Request configuration
            session: Reusable session object
        """
        self.proxy_url = proxy_url
        self.config = config or RequestConfig()
        self._injected_session = session

    def _create_session(self) -> Session:
        """Create a new curl_cffi Session with configured proxy and settings."""
        return Session(
            proxies=self.proxies,
            impersonate=self.config.impersonate,
            verify=self.config.verify_ssl,
            timeout=self.config.timeout
        )

    @property
    def proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration"""
        if not self.proxy_url:
            return None
        return {
            "http": self.proxy_url,
            "https": self.proxy_url,
        }

    @property
    def session(self) -> Session:
        """Get session object (singleton via ManagedSession)."""
        if self._injected_session is not None:
            return self._injected_session
        return self._get_session()

    def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Response:
        """
        Send HTTP request

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL
            **kwargs: Other request parameters

        Returns:
            Response object

        Raises:
            HTTPClientError: Request failed
        """
        # Set default parameters
        kwargs.setdefault("timeout", self.config.timeout)
        kwargs.setdefault("allow_redirects", self.config.follow_redirects)

        # Add proxy configuration
        if self.proxies and "proxies" not in kwargs:
            kwargs["proxies"] = self.proxies

        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, **kwargs)

                # Check response status code
                if response.status_code >= 400:
                    logger.warning(
                        f"HTTP {response.status_code} for {method} {url}"
                        f" (attempt {attempt + 1}/{self.config.max_retries})"
                    )

                    # Retry on server errors
                    if response.status_code >= 500 and attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay * (attempt + 1))
                        continue

                return response

            except (cffi_requests.RequestsError, ConnectionError, TimeoutError) as e:
                last_exception = e
                logger.warning(
                    f"Request failed: {method} {url} (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    break

        raise HTTPClientError(
            f"Request failed, max retries reached: {method} {url} - {last_exception}"
        )

    def get(self, url: str, **kwargs) -> Response:
        """Send GET request"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, data: Any = None, json: Any = None, **kwargs) -> Response:
        """Send POST request"""
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url: str, data: Any = None, json: Any = None, **kwargs) -> Response:
        """Send PUT request"""
        return self.request("PUT", url, data=data, json=json, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        """Send DELETE request"""
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs) -> Response:
        """Send HEAD request"""
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs) -> Response:
        """Send OPTIONS request"""
        return self.request("OPTIONS", url, **kwargs)

    def patch(self, url: str, data: Any = None, json: Any = None, **kwargs) -> Response:
        """Send PATCH request"""
        return self.request("PATCH", url, data=data, json=json, **kwargs)

    def download_file(self, url: str, filepath: str, chunk_size: int = 8192) -> None:
        """
        Download file

        Args:
            url: File URL
            filepath: Save path
            chunk_size: Chunk size

        Raises:
            HTTPClientError: Download failed
        """
        try:
            response = self.get(url, stream=True)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)

        except Exception as e:
            raise HTTPClientError(f"Download failed: {url} - {e}")

    def check_proxy(self, test_url: str = "https://httpbin.org/ip") -> bool:
        """
        Check if proxy is available

        Args:
            test_url: Test URL

        Returns:
            bool: Whether the proxy is available
        """
        if not self.proxy_url:
            return False

        try:
            response = self.get(test_url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def close(self):
        """Close session"""
        if self._injected_session:
            try:
                self._injected_session.close()
            except Exception:
                pass
            self._injected_session = None
        ManagedSession.close(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()