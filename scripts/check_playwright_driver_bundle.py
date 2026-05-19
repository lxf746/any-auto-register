#!/usr/bin/env python3
"""Validate that a PyInstaller onedir bundle contains Playwright's driver."""
from __future__ import annotations

import platform
import sys
from pathlib import Path


def _bundle_root(path: Path) -> Path:
    internal = path / "_internal"
    return internal if internal.is_dir() else path


def check_bundle(path: Path) -> list[str]:
    root = _bundle_root(path)
    driver = root / "playwright" / "driver"
    node_name = "node.exe" if platform.system() == "Windows" else "node"
    required = [
        driver / node_name,
        driver / "package" / "cli.js",
        driver / "package" / "package.json",
    ]
    return [str(item) for item in required if not item.exists()]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_playwright_driver_bundle.py <pyinstaller-onedir>", file=sys.stderr)
        return 2

    missing = check_bundle(Path(argv[1]))
    if missing:
        print("Missing Playwright driver files:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("Playwright driver bundle OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
