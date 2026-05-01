from __future__ import annotations

import time
import threading

import requests
from fastapi import APIRouter

from application.system import SystemService
from core.version import __version__

router = APIRouter(tags=["system"])
service = SystemService()

_RELEASE_API = "https://api.github.com/repos/lxf746/any-auto-register/releases/latest"
_VERSION_CACHE: dict = {}
_VERSION_CACHE_TTL = 600  # 10 分钟，避免 GitHub API rate limit (60/h unauth)
_VERSION_CACHE_LOCK = threading.Lock()


def _fetch_latest_release() -> dict | None:
    """拉 GitHub 最新 release，10min 缓存。"""
    now = time.time()
    with _VERSION_CACHE_LOCK:
        cached = _VERSION_CACHE.get("data")
        cached_at = float(_VERSION_CACHE.get("ts") or 0)
        if cached and (now - cached_at) < _VERSION_CACHE_TTL:
            return cached
    try:
        resp = requests.get(_RELEASE_API, timeout=8)
        if resp.status_code != 200:
            return None
        payload = resp.json() or {}
        result = {
            "tag": str(payload.get("tag_name") or "").lstrip("v"),
            "name": str(payload.get("name") or ""),
            "html_url": str(payload.get("html_url") or ""),
            "body": str(payload.get("body") or "")[:2000],
            "published_at": str(payload.get("published_at") or ""),
        }
        with _VERSION_CACHE_LOCK:
            _VERSION_CACHE["data"] = result
            _VERSION_CACHE["ts"] = now
        return result
    except Exception:
        return None


def _is_newer(latest: str, current: str) -> bool:
    """比较语义化版本号；任一解析失败则比字符串。"""
    def parse(s: str) -> tuple:
        parts = []
        for chunk in str(s or "").split("."):
            num = ""
            for ch in chunk:
                if ch.isdigit():
                    num += ch
                else:
                    break
            parts.append(int(num) if num else 0)
        return tuple(parts)

    if not latest or not current or current == "dev":
        return bool(latest) and current != latest
    try:
        return parse(latest) > parse(current)
    except Exception:
        return latest != current


@router.get("/solver/status")
def solver_status():
    return service.solver_status()


@router.post("/solver/restart")
def solver_restart():
    return service.restart_solver()


@router.get("/version")
def get_version():
    """返回当前版本与 GitHub 最新 release。前端用此判断是否提示更新。"""
    current = __version__
    latest = _fetch_latest_release()
    has_update = bool(latest and _is_newer(latest.get("tag", ""), current))
    return {
        "current": current,
        "latest": latest,
        "has_update": has_update,
    }

