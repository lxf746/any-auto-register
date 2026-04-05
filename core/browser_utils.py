"""Shared browser helpers for headless/headed automation."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import tempfile
from typing import Optional
from urllib.parse import urlparse


_ARTIFACT_ROOT = Path(tempfile.gettempdir()) / "any-auto-register"


def build_proxy_config(proxy: Optional[str]) -> Optional[dict]:
    if not proxy:
        return None
    parsed = urlparse(proxy)
    if not parsed.scheme or not parsed.hostname or not parsed.port:
        return {"server": proxy}
    config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        config["username"] = parsed.username
    if parsed.password:
        config["password"] = parsed.password
    return config


def _safe_artifact_prefix(prefix: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (prefix or "").strip())
    return cleaned.strip("._") or "browser"


def _artifact_base(prefix: str) -> Path:
    _ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return _ARTIFACT_ROOT / f"{_safe_artifact_prefix(prefix)}-{stamp}"


def dump_page_debug(page, prefix: str) -> dict[str, str]:
    base = _artifact_base(prefix)
    screenshot_path = str(base.with_suffix(".png"))
    html_path = str(base.with_suffix(".html"))
    page.screenshot(path=screenshot_path)
    with open(html_path, "w", encoding="utf-8") as file:
        file.write(page.content())
    return {"screenshot": screenshot_path, "html": html_path}
