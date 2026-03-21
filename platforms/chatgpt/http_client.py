"""OpenAI 专用 HTTP 客户端"""
from typing import Any, Dict, Optional, Tuple

from core.http_client import HTTPClient, HTTPClientError, RequestConfig
from .constants import ERROR_MESSAGES
import logging
logger = logging.getLogger(__name__)

class OpenAIHTTPClient(HTTPClient):
    """
    OpenAI 专用 HTTP 客户端
    包含 OpenAI API 特定的请求方法
    """

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        config: Optional[RequestConfig] = None
    ):
        """
        初始化 OpenAI HTTP 客户端

        Args:
            proxy_url: 代理 URL
            config: 请求配置
        """
        super().__init__(proxy_url, config)

        # OpenAI 特定的默认配置
        if config is None:
            self.config.timeout = 30
            self.config.max_retries = 3

        # 默认请求头
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

    def check_ip_location(self) -> Tuple[bool, Optional[str]]:
        """
        检查 IP 地理位置

        Returns:
            Tuple[是否支持, 位置信息]
        """
        try:
            response = self.get("https://cloudflare.com/cdn-cgi/trace", timeout=10)
            trace_text = response.text

            # 解析位置信息
            import re
            loc_match = re.search(r"loc=([A-Z]+)", trace_text)
            loc = loc_match.group(1) if loc_match else None

            # 检查是否支持
            if loc in ["CN", "HK", "MO", "TW"]:
                return False, loc
            return True, loc

        except Exception as e:
            logger.error(f"检查 IP 地理位置失败: {e}")
            return False, None

    def send_openai_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送 OpenAI API 请求

        Args:
            endpoint: API 端点
            method: HTTP 方法
            data: 表单数据
            json_data: JSON 数据
            headers: 请求头
            **kwargs: 其他参数

        Returns:
            响应 JSON 数据

        Raises:
            HTTPClientError: 请求失败
        """
        # 合并请求头
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)

        # 设置 Content-Type
        if json_data is not None and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"
        elif data is not None and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"

        try:
            response = self.request(
                method,
                endpoint,
                data=data,
                json=json_data,
                headers=request_headers,
                **kwargs
            )

            # 检查响应状态码
            response.raise_for_status()

            # 尝试解析 JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"raw_response": response.text}

        except cffi_requests.RequestsError as e:
            raise HTTPClientError(f"OpenAI 请求失败: {endpoint} - {e}")

    def check_sentinel(self, did: str, proxies: Optional[Dict] = None) -> Optional[str]:
        """
        检查 Sentinel 拦截

        Args:
            did: Device ID
            proxies: 代理配置

        Returns:
            Sentinel token 或 None
        """
        from .constants import OPENAI_API_ENDPOINTS

        try:
            sen_req_body = f'{{"p":"","id":"{did}","flow":"authorize_continue"}}'

            response = self.post(
                OPENAI_API_ENDPOINTS["sentinel"],
                headers={
                    "origin": "https://sentinel.openai.com",
                    "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                    "content-type": "text/plain;charset=UTF-8",
                },
                data=sen_req_body,
            )

            if response.status_code == 200:
                return response.json().get("token")
            else:
                logger.warning(f"Sentinel 检查失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Sentinel 检查异常: {e}")
            return None


def create_http_client(
    proxy_url: Optional[str] = None,
    config: Optional[RequestConfig] = None
) -> HTTPClient:
    """
    创建 HTTP 客户端工厂函数

    Args:
        proxy_url: 代理 URL
        config: 请求配置

    Returns:
        HTTPClient 实例
    """
    return HTTPClient(proxy_url, config)


def create_openai_client(
    proxy_url: Optional[str] = None,
    config: Optional[RequestConfig] = None
) -> OpenAIHTTPClient:
    """
    创建 OpenAI HTTP 客户端工厂函数

    Args:
        proxy_url: 代理 URL
        config: 请求配置

    Returns:
        OpenAIHTTPClient 实例
    """
    return OpenAIHTTPClient(proxy_url, config)
