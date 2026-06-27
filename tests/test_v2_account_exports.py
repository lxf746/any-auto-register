"""v2 Account export endpoint tests."""
from __future__ import annotations

import json


def _create_chatgpt_account(client, **overrides):
    """Helper: create a chatgpt account via v2 API."""
    payload = {
        "platform": "chatgpt",
        "email": "export@test.com",
        "password": "TestPass123!",
        **overrides,
    }
    return client.post("/api/v2/accounts/", json=payload)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def test_v2_export_csv(client):
    _create_chatgpt_account(client, email="csv1@test.com")
    resp = client.post("/api/v2/accounts/export/csv", json={"select_all": True})
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "content-disposition" in resp.headers
    assert ".csv" in resp.headers["content-disposition"]


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


def test_v2_export_json(client):
    _create_chatgpt_account(client, email="json1@test.com")
    resp = client.post("/api/v2/accounts/export/json", json={"select_all": True})
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    assert "content-disposition" in resp.headers
    data = json.loads(resp.content)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["email"] == "json1@test.com"


# ---------------------------------------------------------------------------
# Sub2API export
# ---------------------------------------------------------------------------


def test_v2_export_sub2api(client):
    _create_chatgpt_account(client, email="sub2api@test.com")
    resp = client.post("/api/v2/accounts/export/sub2api", json={"select_all": True})
    assert resp.status_code == 200
    assert "content-disposition" in resp.headers


# ---------------------------------------------------------------------------
# CPA export
# ---------------------------------------------------------------------------


def test_v2_export_cpa(client):
    _create_chatgpt_account(client, email="cpa@test.com")
    resp = client.post("/api/v2/accounts/export/cpa", json={"select_all": True})
    assert resp.status_code == 200
    assert "content-disposition" in resp.headers


# ---------------------------------------------------------------------------
# Kiro-Go export
# ---------------------------------------------------------------------------


def test_v2_export_kiro_go(client):
    client.post("/api/v2/accounts/", json={
        "platform": "kiro",
        "email": "kiro@test.com",
        "password": "",
    })
    resp = client.post("/api/v2/accounts/export/kiro-go", json={
        "platform": "kiro",
        "select_all": True,
    })
    assert resp.status_code == 200
    assert "kiro_go_config" in resp.headers.get("content-disposition", "")


# ---------------------------------------------------------------------------
# Any2API export
# ---------------------------------------------------------------------------


def test_v2_export_any2api(client):
    client.post("/api/v2/accounts/", json={"platform": "kiro", "email": "k@test.com", "password": ""})
    client.post("/api/v2/accounts/", json={"platform": "grok", "email": "g@test.com", "password": ""})
    resp = client.post("/api/v2/accounts/export/any2api", json={"select_all": True})
    assert resp.status_code == 200
    assert "any2api_admin" in resp.headers.get("content-disposition", "")
