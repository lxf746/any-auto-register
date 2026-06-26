# Testing Patterns

**Analysis Date:** 2026-06-26

## Test Framework

**Runner:**
- `pytest` >= 8.0.0
- Config: `pytest.ini`

**Assertion Library:**
- Built-in `assert` statements (no pytest plugins for assertion rewriting detected)
- `pytest.raises` for exception testing

**Run Commands:**
```bash
pytest                    # Run all tests (testpaths=tests)
pytest -v                 # Verbose output
pytest tests/test_api_accounts.py  # Run specific file
pytest -k "test_health"   # Run tests matching pattern
```

## Test File Organization

**Location:**
- All tests in `tests/` directory (separate from source)
- One standalone test at project root: `test_kiro_qa.py` (manual QA script, not part of pytest suite)

**Naming:**
- `test_{module_or_feature}.py` (e.g., `test_api_health.py`, `test_api_accounts.py`, `test_sms_provider.py`)
- Test functions: `test_{description}` (e.g., `test_health`, `test_create_account`, `test_list_accounts_empty`)
- Test classes: `Test{Subject}` (e.g., `TestAny2ApiClient`, `TestSmsActivateProvider`, `TestCreateSmsProvider`)

**Structure:**
```
tests/
├── conftest.py                    # Shared fixtures (DB setup, test client)
├── test_api_health.py             # API endpoint tests
├── test_api_accounts.py           # Account CRUD tests
├── test_api_stats.py              # Stats endpoint tests
├── test_api_proxies.py            # Proxy management tests
├── test_api_lifecycle.py          # Lifecycle API tests
├── test_any2api_sync.py           # Unit tests (mocked)
├── test_proxy_providers.py        # Unit tests (mocked)
├── test_sms_provider.py           # Unit tests (mocked)
├── test_tasks_herosms.py          # Integration tests
├── test_validity_recovery.py      # Integration tests (DB + monkeypatch)
├── test_windsurf_platform.py      # Platform-specific tests
└── test_chatgpt_oauth_requirements.py  # Platform-specific tests
```

## Test Structure

**Function-based tests (most common):**
```python
"""Account CRUD endpoint tests."""
from __future__ import annotations

def test_create_account(client):
    resp = client.post("/api/accounts", json={
        "platform": "chatgpt",
        "email": "test@example.com",
        "password": "TestPass123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "chatgpt"
    assert "id" in data
```

**Class-based tests (for grouped unit tests):**
```python
class TestAny2ApiClient:
    def test_login_success(self):
        client = Any2ApiClient("http://localhost:8099", "changeme")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "token": "abc123"}
        with patch("core.any2api_sync.requests.post", return_value=mock_resp):
            assert client._login() is True

    def test_login_failure(self):
        client = Any2ApiClient("http://localhost:8099", "wrong")
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("core.any2api_sync.requests.post", return_value=mock_resp):
            assert client._login() is False
```

**Helper functions in test files:**
```python
def _create_account(client, **overrides):
    payload = {
        "platform": "chatgpt",
        "email": "test@example.com",
        "password": "TestPass123!",
        **overrides,
    }
    return client.post("/api/accounts", json=payload)

def _make_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"
```

## Mocking

**Framework:** `unittest.mock` (stdlib)

**Patterns:**

`patch` context manager (most common):
```python
from unittest.mock import patch, MagicMock

def test_push_kiro(self):
    client = Any2ApiClient("http://localhost:8099", "changeme")
    client._session_cookie = "test-session"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"account": {"id": "123"}}
    with patch("core.any2api_sync.requests.post", return_value=mock_resp):
        assert client.push_kiro("test-token", name="test@test.com") is True
```

`monkeypatch` fixture (for attribute replacement):
```python
def test_sms_activate(test):
    provider = create_sms_provider("sms_activate", {"sms_activate_api_key": "test123"})
    assert isinstance(provider, SmsActivateProvider)

def test_provider_is_created_lazily(self, monkeypatch):
    monkeypatch.setattr("core.base_sms.create_sms_provider", lambda provider_key, config: FakeProvider())
    callback, cleanup = create_phone_callbacks(...)
```

Inline mock classes:
```python
class _AlwaysValidPlatform:
    def __init__(self, config: RegisterConfig | None = None):
        self.config = config
    def check_valid(self, account) -> bool:
        return True
```

**What to Mock:**
- External HTTP calls (`requests.post`, `requests.get`, `curl_cffi.requests.post`)
- Platform registries (`core.registry.get`, `providers.registry.create_provider`)
- SMS/captcha provider creation (`core.base_sms.create_sms_provider`)
- File system operations (`sms_module.hero_sms_cache_file`)
- Time-dependent code (`sms_module.time.time()`)

**What NOT to Mock:**
- Database operations (use real SQLite test database via `conftest.py`)
- FastAPI TestClient (use real client with test database)
- Domain dataclasses (pure data, no side effects)

## Fixtures and Factories

**Location:** `tests/conftest.py`

**Database fixture (autouse):**
```python
@pytest.fixture(autouse=True)
def _reset_db():
    """Drop and recreate all tables between tests for full isolation."""
    SQLModel.metadata.drop_all(_db_module.engine)
    SQLModel.metadata.create_all(_db_module.engine)
    yield
```

**Test client fixture:**
```python
@pytest.fixture()
def client():
    """FastAPI TestClient with a clean database."""
    from main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
```

**Database isolation:**
- Uses temporary SQLite file (`tempfile.NamedTemporaryFile(suffix=".db")`)
- Environment variable `ACCOUNT_MANAGER_DATABASE_URL` set before any app imports
- Engine monkey-patched in conftest before app creation
- All tables dropped and recreated between each test

**Session cleanup:**
```python
def pytest_sessionfinish(session, exitstatus):
    """Clean up temp DB file."""
    try:
        os.unlink(_TEST_DB_PATH)
    except OSError:
        pass
```

## Test Types

**API Integration Tests (majority):**
- Use FastAPI `TestClient` with real test database
- Test full request/response cycle through API → application → infrastructure → DB
- Example: `tests/test_api_accounts.py`, `tests/test_api_health.py`, `tests/test_api_proxies.py`

**Unit Tests with Mocking:**
- Mock external dependencies (HTTP APIs, file system)
- Test individual class/function logic in isolation
- Example: `tests/test_any2api_sync.py`, `tests/test_proxy_providers.py`, `tests/test_sms_provider.py`

**Platform-Specific Tests:**
- Test platform registration flows, token handling, device switching
- May use monkeypatch to mock platform-specific APIs
- Example: `tests/test_validity_recovery.py`, `tests/test_windsurf_platform.py`

**No E2E Tests:**
- No browser-based end-to-end tests detected
- No Playwright/Selenium test integration

## Coverage

**Requirements:** None enforced

**No coverage configuration detected** (no `.coveragerc`, no `--cov` in pytest config)

## Test Configuration

**`pytest.ini`:**
```ini
[pytest]
testpaths = tests
pythonpath = .
```

**Key settings:**
- `testpaths = tests` — pytest only looks in `tests/` directory
- `pythonpath = .` — project root added to sys.path for imports
- No markers, plugins, or custom options configured

## Common Patterns

**Testing API error responses:**
```python
def test_get_account_not_found(client):
    resp = client.get("/api/accounts/99999")
    assert resp.status_code == 404
```

**Testing with database setup:**
```python
def test_resolve_sms_provider_for_task_uses_saved_herosms_default():
    repo = ProviderSettingsRepository()
    repo.save(setting_id=None, provider_type="sms", provider_key="herosms", ...)
    provider_key, settings = _resolve_sms_provider_for_task({})
    assert provider_key == "herosms"
```

**Testing exception raising:**
```python
def test_unknown_provider(self):
    with pytest.raises(RuntimeError, match="unknown"):
        create_sms_provider("unknown", {})

def test_api_extract_missing_url(self):
    with pytest.raises(RuntimeError, match="not configured"):
        create_proxy_provider("api_extract", {})
```

**Testing callback side effects:**
```python
def test_provider_is_created_lazily_and_cleanup_cancels_pending_activation(self, monkeypatch):
    events = []
    class FakeProvider:
        def get_number(self, *, service: str, country: str = ""):
            events.append(("get_number", service, country))
            return SmsActivation(activation_id="act_1", phone_number="+15551234567")
    monkeypatch.setattr("core.base_sms.create_sms_provider", lambda provider_key, config: FakeProvider())
    callback, cleanup = create_phone_callbacks(...)
    assert callback() == "+15551234567"
    cleanup()
    assert ("get_number", "chatgpt", "us") in events
```

**Testing dict/list response structure:**
```python
def test_stats_overview_empty(client):
    resp = client.get("/api/stats/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_registrations"] == 0
    assert data["success"] == 0
    assert data["success_rate"] == 0
```

---

*Testing analysis: 2026-06-26*
