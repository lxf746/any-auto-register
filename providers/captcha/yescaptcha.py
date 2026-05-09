"""YesCaptcha — cloud Turnstile + CloudFlare5s solver."""
from core.base_captcha import BaseCaptcha
from core.tls import insecure_request
from providers.registry import register_provider


@register_provider("captcha", "yescaptcha_api")
class YesCaptcha(BaseCaptcha):
    def __init__(self, client_key: str, api_host: str = "https://api.yescaptcha.com"):
        self.client_key = str(client_key or "").strip()
        self.api = str(api_host or "https://api.yescaptcha.com").rstrip("/")

    @classmethod
    def from_config(cls, config: dict) -> 'YesCaptcha':
        client_key = str(config.get("yescaptcha_key", "") or "")
        if not client_key:
            raise RuntimeError("YesCaptcha Key 未配置")
        api_host = str(config.get("yescaptcha_api_host", "") or "").strip() or "https://api.yescaptcha.com"
        return cls(client_key, api_host=api_host)

    def _create_task(self, task: dict) -> str:
        import requests

        r = insecure_request(
            requests.post,
            f"{self.api}/createTask",
            json={"clientKey": self.client_key, "task": task},
            timeout=30,
        )
        data = r.json()
        if int(data.get("errorId", 0) or 0) != 0:
            raise RuntimeError(f"YesCaptcha 创建任务失败: {data}")
        task_id = str(data.get("taskId") or "").strip()
        if not task_id:
            raise RuntimeError(f"YesCaptcha 未返回 taskId: {data}")
        return task_id

    def _poll_task_result(self, task_id: str, *, max_rounds: int = 60) -> dict:
        import requests
        import time

        for _ in range(max_rounds):
            time.sleep(3)
            d = insecure_request(
                requests.post,
                f"{self.api}/getTaskResult",
                json={"clientKey": self.client_key, "taskId": task_id},
                timeout=30,
            ).json()
            if d.get("status") == "ready":
                return d
            if int(d.get("errorId", 0) or 0) != 0:
                raise RuntimeError(f"YesCaptcha 错误: {d}")
        raise TimeoutError("YesCaptcha 任务超时")

    def solve_turnstile(self, page_url: str, site_key: str) -> str:
        task_id = self._create_task(
            {
                "type": "TurnstileTaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        )
        d = self._poll_task_result(task_id, max_rounds=60)
        token = str((d.get("solution") or {}).get("token") or "").strip()
        if not token:
            raise RuntimeError(f"YesCaptcha Turnstile 未返回 token: {d}")
        return token

    def solve_cloudflare5s(self, website_url: str, *, proxy: str, rq_data: dict | None = None) -> dict:
        proxy_url = str(proxy or "").strip()
        if not proxy_url:
            raise RuntimeError("YesCaptcha CloudFlare5s 需要代理（proxy）")

        task: dict = {
            "type": "CloudFlareTaskS3",
            "websiteURL": str(website_url or "").strip(),
            "proxy": proxy_url,
            "requiredCookies": ["cf_clearance", "__cf_bm", "_cfuvid"],
            "waitLoad": False,
        }
        if rq_data:
            task.update(dict(rq_data))

        task_id = self._create_task(task)
        d = self._poll_task_result(task_id, max_rounds=40)
        solution = dict(d.get("solution") or {})
        cookies = dict(solution.get("cookies") or {})
        request_headers = dict(solution.get("request_headers") or {})
        response_headers = dict(solution.get("headers") or {})
        ua = str(solution.get("user_agent") or "")
        if ua and "user-agent" not in request_headers:
            request_headers["user-agent"] = ua
        merged_headers = {**response_headers, **request_headers}

        return {
            "cookies": cookies,
            "headers": merged_headers,
            "tls_version": str(solution.get("tlsVersion") or ""),
            "raw_solution": solution,
        }

    def solve_image(self, image_b64: str) -> str:
        raise NotImplementedError
