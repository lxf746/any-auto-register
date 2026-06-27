"""v2 Account CRUD, stats, and import endpoint tests."""
from __future__ import annotations


def _create_v2_account(client, **overrides):
    """Helper: POST to /api/v2/accounts/ with sensible defaults."""
    payload = {
        "platform": "chatgpt",
        "email": "v2test@example.com",
        "password": "TestPass123!",
        **overrides,
    }
    return client.post("/api/v2/accounts/", json=payload)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_v2_create_account(client):
    resp = _create_v2_account(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    data = body["data"]
    assert "id" in data
    assert data["platform"] == "chatgpt"
    assert data["email"] == "v2test@example.com"


def test_v2_create_account_missing_platform(client):
    resp = client.post("/api/v2/accounts/", json={"email": "a@b.com", "password": "x"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------


def test_v2_get_account_by_id(client):
    create_resp = _create_v2_account(client)
    account_id = create_resp.json()["data"]["id"]
    resp = client.get(f"/api/v2/accounts/{account_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["email"] == "v2test@example.com"


def test_v2_get_account_not_found(client):
    resp = client.get("/api/v2/accounts/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update (PATCH)
# ---------------------------------------------------------------------------


def test_v2_update_account(client):
    create_resp = _create_v2_account(client)
    account_id = create_resp.json()["data"]["id"]
    resp = client.patch(f"/api/v2/accounts/{account_id}", json={"password": "NewPass456!"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["password"] == "NewPass456!"


def test_v2_update_account_not_found(client):
    resp = client.patch("/api/v2/accounts/99999", json={"password": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_v2_delete_account(client):
    create_resp = _create_v2_account(client)
    account_id = create_resp.json()["data"]["id"]
    del_resp = client.delete(f"/api/v2/accounts/{account_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["ok"] is True
    # Verify it's gone
    get_resp = client.get(f"/api/v2/accounts/{account_id}")
    assert get_resp.status_code == 404


def test_v2_delete_account_not_found(client):
    resp = client.delete("/api/v2/accounts/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_v2_list_accounts(client):
    _create_v2_account(client, email="a@test.com")
    _create_v2_account(client, email="b@test.com")
    resp = client.get("/api/v2/accounts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["total"] == 2


def test_v2_list_accounts_filter_by_platform(client):
    _create_v2_account(client, platform="chatgpt", email="c1@test.com")
    _create_v2_account(client, platform="cursor", email="c2@test.com")
    resp = client.get("/api/v2/accounts", params={"platform": "cursor"})
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["platform"] == "cursor"


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_v2_account_stats(client):
    _create_v2_account(client)
    resp = client.get("/api/v2/accounts/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "total" in body["data"]


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def test_v2_import_accounts(client):
    resp = client.post("/api/v2/accounts/import", json={
        "platform": "chatgpt",
        "lines": [
            "import@test.com Pass123!",
            "import2@test.com Pass456!",
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["created"] >= 2
