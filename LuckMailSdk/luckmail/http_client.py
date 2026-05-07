"""
核心 HTTP 客户端（基于 curl_cffi）
支持同步/异步双模式，智能识别调用上下文自动切换

支持 TLS 指纹模拟，避免被目标网站识别为机器人。
"""

import asyncio
import hashlib
import hmac
import json
import secrets
import threading
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from curl_cffi import requests as curl_requests

from .exceptions import APIError, AuthError, NetworkError


def _is_async_context() -> bool:
    """检测当前是否处于异步上下文（事件循环正在运行）"""
    try:
        loop = asyncio.get_event_loop()
        return loop.is_running()
    except RuntimeError:
        return False


def _generate_hmac_signature(api_secret: str, api_key: str, timestamp: str, nonce: str) -> str:
    """生成 HMAC-SHA256 签名

    签名内容：api_key + timestamp + nonce，使用 api_secret 作为密钥
    """
    message = f"{api_key}{timestamp}{nonce}"
    signature = hmac.new(
        api_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature


class _SyncRunner:
    """同步运行异步函数的工具类"""

    _lock = threading.Lock()
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _thread: Optional[threading.Thread] = None

    @classmethod
    def _ensure_loop(cls):
        """确保后台事件循环正在运行"""
        with cls._lock:
            if cls._loop is None or not cls._loop.is_running():
                cls._loop = asyncio.new_event_loop()
                cls._thread = threading.Thread(
                    target=cls._loop.run_forever,
                    daemon=True,
                    name="LuckMailSdk-EventLoop"
                )
                cls._thread.start()

    @classmethod
    def run(cls, coro) -> Any:
        """在后台事件循环中同步运行协程"""
        cls._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, cls._loop)
        return future.result()


class LuckMailHttpClient:
    """
    LuckMail HTTP 客户端（基于 curl_cffi）

    使用 curl_cffi 作为底层 HTTP 库，支持 TLS 指纹模拟。
    自动识别调用上下文（同步/异步），提供统一的请求接口。

    Args:
        base_url: API 基础 URL，如 https://your-domain.com
        api_key: API Key（必填）
        api_secret: API Secret（可选，用于 HMAC 签名验证，安全性更高）
        timeout: 请求超时时间（秒），默认 30
        use_hmac: 是否使用 HMAC 签名验证，默认 False（使用时需提供 api_secret）
        impersonate: 浏览器指纹模拟，默认 "chrome"（可选 "firefox"、"safari" 等）
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_secret: Optional[str] = None,
        timeout: float = 30.0,
        use_hmac: bool = False,
        impersonate: str = "chrome",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.use_hmac = use_hmac and api_secret is not None
        self.impersonate = impersonate

        # 同步 Session（延迟初始化）
        self._sync_session: Optional[curl_requests.Session] = None
        # 异步 Session（延迟初始化）
        self._async_session: Optional[Any] = None

    def _get_sync_session(self) -> curl_requests.Session:
        """获取或创建同步 Session"""
        if self._sync_session is None:
            self._sync_session = curl_requests.Session(
                impersonate=self.impersonate,
                timeout=self.timeout,
            )
        return self._sync_session

    async def _get_async_session(self):
        """获取或创建异步 Session"""
        if self._async_session is None:
            self._async_session = curl_requests.AsyncSession(
                impersonate=self.impersonate,
                timeout=self.timeout,
            )
        return self._async_session

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头（含鉴权信息）"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.use_hmac and self.api_secret:
            # HMAC 签名模式
            timestamp = str(int(time.time()))
            nonce = secrets.token_hex(16)
            signature = _generate_hmac_signature(
                self.api_secret, self.api_key, timestamp, nonce
            )
            headers["X-API-Key"] = self.api_key
            headers["X-Timestamp"] = timestamp
            headers["X-Nonce"] = nonce
            headers["X-Signature"] = signature
        elif self.api_key:
            # 普通 API Key 模式（推荐）
            headers["X-API-Key"] = self.api_key

        return headers

    def _build_url(self, path: str, params: Optional[Dict] = None) -> str:
        """构建完整 URL"""
        url = f"{self.base_url}{path}"
        if params:
            # 过滤 None 值
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                url = f"{url}?{urlencode(filtered)}"
        return url

    def _parse_response(self, status_code: int, content: bytes) -> Any:
        """解析响应数据"""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # 非 JSON 响应（如文件流）直接返回字节内容
            return content

        if not isinstance(data, dict):
            return data

        code = data.get("code", -1)
        message = data.get("message", "Unknown error")

        if code != 0:
            if status_code == 401 or code == 401:
                raise AuthError(message)
            raise APIError(code, message, data.get("data"))

        return data.get("data")

    # ===================== 异步方法 =====================

    async def _async_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Any:
        """异步 HTTP 请求"""
        session = await self._get_async_session()
        headers = self._build_headers()
        url = self._build_url(path, params)

        try:
            if method.upper() == "GET":
                response = await session.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await session.post(
                    url, headers=headers, json=json_data or {}
                )
            elif method.upper() == "PUT":
                response = await session.put(
                    url, headers=headers, json=json_data or {}
                )
            elif method.upper() == "DELETE":
                response = await session.delete(url, headers=headers)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")

            return self._parse_response(response.status_code, response.content)

        except (AuthError, APIError):
            raise
        except Exception as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg:
                from .exceptions import TimeoutError as LuckTimeoutError
                raise LuckTimeoutError(f"请求超时: {path}") from e
            raise NetworkError(f"请求失败: {e}") from e

    async def _async_get_stream(self, path: str, params: Optional[Dict] = None) -> bytes:
        """异步获取流式响应（文件下载等）"""
        session = await self._get_async_session()
        headers = self._build_headers()
        url = self._build_url(path, params)

        try:
            response = await session.get(url, headers=headers)
            return response.content
        except Exception as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg:
                from .exceptions import TimeoutError as LuckTimeoutError
                raise LuckTimeoutError(f"请求超时: {path}") from e
            raise NetworkError(f"网络错误: {e}") from e

    async def aclose(self):
        """关闭异步客户端"""
        if self._async_session is not None:
            await self._async_session.close()
            self._async_session = None

    # ===================== 同步方法 =====================

    def _sync_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Any:
        """同步 HTTP 请求（使用 curl_cffi）"""
        session = self._get_sync_session()
        headers = self._build_headers()
        url = self._build_url(path, params)

        try:
            if method.upper() == "GET":
                response = session.get(url, headers=headers)
            elif method.upper() == "POST":
                response = session.post(
                    url, headers=headers, json=json_data or {}
                )
            elif method.upper() == "PUT":
                response = session.put(
                    url, headers=headers, json=json_data or {}
                )
            elif method.upper() == "DELETE":
                response = session.delete(url, headers=headers)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")

            return self._parse_response(response.status_code, response.content)

        except (AuthError, APIError):
            raise
        except Exception as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg:
                from .exceptions import TimeoutError as LuckTimeoutError
                raise LuckTimeoutError(f"请求超时: {path}") from e
            raise NetworkError(f"请求失败: {e}") from e

    def _sync_get_stream(self, path: str, params: Optional[Dict] = None) -> bytes:
        """同步获取流式响应"""
        session = self._get_sync_session()
        headers = self._build_headers()
        url = self._build_url(path, params)

        try:
            response = session.get(url, headers=headers)
            return response.content
        except Exception as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg:
                from .exceptions import TimeoutError as LuckTimeoutError
                raise LuckTimeoutError(f"请求超时: {path}") from e
            raise NetworkError(f"网络错误: {e}") from e

    # ===================== 统一接口（智能识别同步/异步）=====================

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ):
        """
        统一请求接口，智能识别调用上下文：
        - 在 async 函数中调用：自动返回协程，需要 await
        - 在普通函数中调用：直接返回结果

        使用示例：
            # 同步调用
            result = client.request("GET", "/api/v1/openapi/user/info")

            # 异步调用
            result = await client.request("GET", "/api/v1/openapi/user/info")
        """
        if _is_async_context():
            return self._async_request(method, path, params=params, json_data=json_data)
        else:
            return self._sync_request(method, path, params=params, json_data=json_data)

    def get_stream(self, path: str, params: Optional[Dict] = None):
        """
        流式 GET 请求（用于文件下载），智能识别同步/异步上下文
        """
        if _is_async_context():
            return self._async_get_stream(path, params=params)
        else:
            return self._sync_get_stream(path, params=params)

    def close(self):
        """关闭同步客户端资源"""
        if self._sync_session is not None:
            self._sync_session.close()
            self._sync_session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
