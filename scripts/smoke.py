#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api"
    endpoints = [
        ("health", f"{base}/health"),
        ("ready", f"{base}/ready"),
        ("platforms", f"{base}/platforms"),
        ("config", f"{base}/config"),
        ("config_options", f"{base}/config/options"),
        ("tasks", f"{base}/tasks"),
        ("proxies", f"{base}/proxies"),
    ]
    failed = False
    for name, url in endpoints:
        try:
            data = fetch(url)
            label = list(data)[:5] if isinstance(data, dict) else type(data).__name__
            print(f"[OK] {name:<14} {url} -> {label}")
        except urllib.error.URLError as exc:
            failed = True
            print(f"[FAIL] {name:<14} {url} -> {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
