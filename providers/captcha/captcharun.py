"""CaptchaRun provider with Turnstile + CloudFlare5s support."""
from __future__ import annotations

import time
from urllib.parse import urlparse

import requests

from core.base_captcha import BaseCaptcha
from core.tls import insecure_request
from providers.registry import register_provider


def _parse_proxy(proxy_url: str) -> tuple[str, int, str, str]:
    u = urlparse(str(proxy_url or "").strip())
    if not u.scheme or not u.hostname or not u.port:
        raise RuntimeError("CaptchaRun CloudFlare5s 代理格式无效，应为 http://user:pass@host:port")
    login = str(u.username or "")
    password = str(u.password or "")
    if not login or not password:
        raise RuntimeError("CaptchaRun CloudFlare5s 需要带账号密码的代理")
    return u.hostname, int(u.port), login, password


@register_provider("captcha", "captcharun_api")
class CaptchaRunCaptcha(BaseCaptcha):
    def __init__(self, api_key: str, api_host: str = "https://api.captcha-run.com"):
        self.api_key = str(api_key or "").strip()
        self.api = str(api_host or "https://api.captcha-run.com").rstrip("/")

    @classmethod
    def from_config(cls, config: dict) -> "CaptchaRunCaptcha":
        api_key = str(config.get("captcharun_api_key", "") or "").strip()
        if not api_key:
            raise RuntimeError("CaptchaRun API Key 未配置")
        host = str(config.get("captcharun_api_host", "") or "").strip() or "https://api.captcha-run.com"
        return cls(api_key=api_key, api_host=host)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def solve_cloudflare5s(self, website_url: str, *, proxy: str, rq_data: dict | None = None) -> dict:
        host, port, login, password = _parse_proxy(proxy)
        payload = {
            "captchaType": "CloudFlare5s",
            "siteReferer": str(website_url or "").strip(),
            "host": host,
            "port": port,
            "login": login,
            "password": password,
        }
        max_rounds = 40
        if rq_data:
            rq = dict(rq_data)
            # allow caller to control polling rounds without leaking into API payload
            if "max_rounds" in rq:
                try:
                    max_rounds = max(1, int(rq.pop("max_rounds")))
                except Exception:
                    pass
            payload.update(rq)

        create = insecure_request(
            requests.post,
            f"{self.api}/v2/tasks",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        create.raise_for_status()
        task_data = create.json()
        task_id = str(task_data.get("id") or task_data.get("taskId") or "").strip()
        if not task_id:
            raise RuntimeError(f"CaptchaRun 创建任务失败: {task_data}")

        for _ in range(max_rounds):
            time.sleep(3)
            query = insecure_request(
                requests.get,
                f"{self.api}/v2/tasks/{task_id}",
                headers=self._headers(),
                timeout=30,
            )
            query.raise_for_status()
            data = query.json()
            status = str(data.get("status") or "").lower()
            if status in {"success", "ready"}:
                response = dict(data.get("response") or {})
                return {
                    "cookies": dict(response.get("cookies") or {}),
                    "headers": {"user-agent": str(response.get("ua") or "")},
                    "tls_version": "",
                    "raw_solution": response,
                }
            if status in {"failed", "error"}:
                raise RuntimeError(f"CaptchaRun CloudFlare5s 失败: {data}")
        raise TimeoutError("CaptchaRun CloudFlare5s 超时")

    def solve_turnstile(self, page_url: str, site_key: str) -> str:
        payload = {
            "captchaType": "Turnstile",
            "siteReferer": str(page_url or "").strip(),
            "siteKey": str(site_key or "").strip(),
        }
        create = insecure_request(
            requests.post,
            f"{self.api}/v2/tasks",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        create.raise_for_status()
        task_data = create.json()
        task_id = str(task_data.get("taskId") or task_data.get("id") or "").strip()
        if not task_id:
            raise RuntimeError(f"CaptchaRun Turnstile 创建任务失败: {task_data}")

        for _ in range(40):
            time.sleep(3)
            query = insecure_request(
                requests.get,
                f"{self.api}/v2/tasks/{task_id}",
                headers=self._headers(),
                timeout=30,
            )
            query.raise_for_status()
            data = query.json()
            status = str(data.get("status") or "").lower()
            if status in {"success", "ready"}:
                token = str((data.get("response") or {}).get("token") or "").strip()
                if token:
                    return token
                raise RuntimeError(f"CaptchaRun Turnstile 未返回 token: {data}")
            if status in {"failed", "error"}:
                raise RuntimeError(f"CaptchaRun Turnstile 失败: {data}")
        raise TimeoutError("CaptchaRun Turnstile 超时")

    def solve_image(self, image_b64: str) -> str:
        raise NotImplementedError
