"""Registration stats dashboard API tests — v2 endpoints."""
from __future__ import annotations


def test_stats_overview_empty(client):
    resp = client.get("/api/v2/stats/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["total_registrations"] == 0
    assert data["success"] == 0
    assert data["failed"] == 0
    assert data["success_rate"] == 0
    assert data["total_accounts"] == 0


def test_stats_by_platform_empty(client):
    resp = client.get("/api/v2/stats/by-platform")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"] == []


def test_stats_by_day_empty(client):
    resp = client.get("/api/v2/stats/by-day")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"] == []


def test_stats_by_day_with_platform_filter(client):
    resp = client.get("/api/v2/stats/by-day", params={"days": 7, "platform": "chatgpt"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert isinstance(body["data"], list)


def test_stats_by_proxy_empty(client):
    resp = client.get("/api/v2/stats/by-proxy")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"] == []


def test_stats_by_proxy_with_data(client):
    # Add a proxy via v2 endpoint
    client.post("/api/v2/proxies", json={"url": "http://1.2.3.4:8080", "region": "US"})
    resp = client.get("/api/v2/stats/by-proxy")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    data = body["data"]
    assert len(data) == 1
    assert data[0]["url"] == "http://1.2.3.4:8080"
    assert data[0]["success_rate"] == 0


def test_stats_errors_empty(client):
    resp = client.get("/api/v2/stats/errors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"] == []


def test_stats_errors_with_platform_filter(client):
    resp = client.get("/api/v2/stats/errors", params={"days": 7, "platform": "cursor"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert isinstance(body["data"], list)
