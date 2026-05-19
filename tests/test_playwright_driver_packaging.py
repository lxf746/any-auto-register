from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_playwright_driver_bundle import check_bundle


def _write_driver(root: Path, node_name: str) -> None:
    driver = root / "_internal" / "playwright" / "driver"
    (driver / "package").mkdir(parents=True)
    (driver / node_name).write_text("", encoding="utf-8")
    (driver / "package" / "cli.js").write_text("", encoding="utf-8")
    (driver / "package" / "package.json").write_text("{}", encoding="utf-8")


def test_check_playwright_driver_bundle_accepts_complete_bundle(tmp_path, monkeypatch):
    node_name = "node.exe"
    monkeypatch.setattr("platform.system", lambda: "Windows")
    _write_driver(tmp_path / "backend", node_name)

    assert check_bundle(tmp_path / "backend") == []


def test_check_playwright_driver_bundle_reports_missing_node(tmp_path, monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Windows")
    _write_driver(tmp_path / "backend", "node")

    missing = check_bundle(tmp_path / "backend")

    assert any(item.endswith("playwright\\driver\\node.exe") or item.endswith("playwright/driver/node.exe") for item in missing)
