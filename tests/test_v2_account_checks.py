"""v2 Account check endpoint tests."""
from __future__ import annotations


def _create_v2_account(client, **overrides):
    """Helper: create an account via v2 API."""
    payload = {
        "platform": "chatgpt",
        "email": "check@test.com",
        "password": "TestPass123!",
        **overrides,
    }
    return client.post("/api/v2/accounts/", json=payload)


# ---------------------------------------------------------------------------
# Check all
# ---------------------------------------------------------------------------


def test_v2_check_all(client):
    resp = client.post("/api/v2/accounts/check-all")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "task_id" in body["data"] or "id" in body["data"]


def test_v2_check_all_with_platform(client):
    resp = client.post("/api/v2/accounts/check-all", params={"platform": "chatgpt"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True


# ---------------------------------------------------------------------------
# Check one
# ---------------------------------------------------------------------------


def test_v2_check_one(client):
    create_resp = _create_v2_account(client)
    account_id = create_resp.json()["data"]["id"]
    resp = client.post(f"/api/v2/accounts/check-one/{account_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "task_id" in body["data"] or "id" in body["data"]


def test_v2_check_one_not_found(client):
    resp = client.post("/api/v2/accounts/check-one/99999")
    assert resp.status_code == 404
