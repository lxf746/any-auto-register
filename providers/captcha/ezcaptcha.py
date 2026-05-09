"""EZ-Captcha provider with Turnstile + CloudFlare5s support."""
from __future__ import annotations

import time
from typing import Any

import requests

from core.base_captcha import BaseCaptcha
from core.tls import insecure_request
from providers.registry import register_provider


@register_provider("captcha", "ezcaptcha_api")
class EzCaptcha(BaseCaptcha):
    def __init__(self, client_key: str, api_host: str = "https://api.ez-captcha.com"):
        self.client_key = str(client_key or "").strip()
        self.api = str(api_host or "https://api.ez-captcha.com").rstrip("/")

    @classmethod
    def from_config(cls, config: dict) -> "EzCaptcha":
        client_key = str(config.get("ezcaptcha_key", "") or "").strip()
        if not client_key:
            raise RuntimeError("EZ-Captcha Key 未配置")
        host = str(config.get("ezcaptcha_api_host", "") or "").strip() or "https://api.ez-captcha.com"
        return cls(client_key=client_key, api_host=host)

    def _create_task(self, task: dict[str, Any]) -> str:
        r = insecure_request(
            requests.post,
            f"{self.api}/createTask",
            json={"clientKey": self.client_key, "task": task},
            timeout=30,
        )
        data = r.json()
        if int(data.get("errorId", 0) or 0) != 0:
            raise RuntimeError(f"EZ-Captcha 创建任务失败: {data}")
        task_id = str(data.get("taskId") or "").strip()
        if not task_id:
            raise RuntimeError(f"EZ-Captcha 未返回 taskId: {data}")
        return task_id

    def _poll_task_result(self, task_id: str, *, max_wait_seconds: int = 120) -> dict[str, Any]:
        rounds = max(1, int(max_wait_seconds / 3))
        for _ in range(rounds):
            time.sleep(3)
            data = insecure_request(
                requests.post,
                f"{self.api}/getTaskResult",
                json={"clientKey": self.client_key, "taskId": task_id},
                timeout=30,
            ).json()
            if int(data.get("errorId", 0) or 0) != 0:
                raise RuntimeError(f"EZ-Captcha 任务失败: {data}")
            if str(data.get("status", "")).lower() == "ready":
                return data
        raise TimeoutError("EZ-Captcha 任务超时")

    def solve_turnstile(self, page_url: str, site_key: str) -> str:
        task_type = "CloudFlareTurnstileTaskProxyless"
        task_id = self._create_task(
            {
                "type": task_type,
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        )
        data = self._poll_task_result(task_id, max_wait_seconds=180)
        solution = dict(data.get("solution") or {})
        token = str(solution.get("token") or "")
        if not token:
            raise RuntimeError(f"EZ-Captcha Turnstile 未返回 token: {data}")
        return token

    def solve_cloudflare5s(self, website_url: str, *, proxy: str, rq_data: dict | None = None) -> dict[str, Any]:
        proxy_url = str(proxy or "").strip()
        if not proxy_url:
            raise RuntimeError("EZ-Captcha CloudFlare5s 需要代理（proxy）")
        task: dict[str, Any] = {
            "type": "CloudFlare5STask",
            "websiteURL": str(website_url or "").strip(),
            "proxy": proxy_url,
        }
        if rq_data:
            task["rqData"] = dict(rq_data)
        task_id = self._create_task(task)
        data = self._poll_task_result(task_id, max_wait_seconds=120)
        solution = dict(data.get("solution") or {})
        headers = dict(solution.get("header") or {})
        cookies = dict(solution.get("cookies") or {})
        return {
            "cookies": cookies,
            "headers": headers,
            "tls_version": str(solution.get("tlsVersion") or ""),
            "raw_solution": solution,
        }

    def solve_image(self, image_b64: str) -> str:
        raise NotImplementedError
