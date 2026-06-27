"""Shared test fixtures.

Uses a temporary file-based SQLite database with check_same_thread=False
so that the app's background threads (scheduler, task_runtime) can share it.

When ACCOUNT_MANAGER_DATABASE_URL is set to a PostgreSQL URL before import,
tests run against PostgreSQL instead of SQLite.
"""
from __future__ import annotations

import os
import tempfile


def _is_test_pg() -> bool:
    """Return True if the test database URL points to PostgreSQL."""
    url = os.environ.get("ACCOUNT_MANAGER_DATABASE_URL", "")
    return url.startswith("postgresql+asyncpg://") or url.startswith("postgresql://")


# Create a temp DB file BEFORE any application code imports core.db
_pg_url = os.environ.get("ACCOUNT_MANAGER_DATABASE_URL", "")
if _is_test_pg():
    # PostgreSQL mode — use the URL from the environment directly
    _TEST_DB_PATH = ""  # not used for PG
else:
    _tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp.close()
    _TEST_DB_PATH = _tmp.name
    os.environ["ACCOUNT_MANAGER_DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

import pytest
from sqlmodel import SQLModel, create_engine

# Patch the engine before the app is created
from core import db as _db_module
from core.db.engine import _create_sync_engine

if _is_test_pg():
    _db_module.engine = _create_sync_engine(
        os.environ["ACCOUNT_MANAGER_DATABASE_URL"],
    )
else:
    _db_module.engine = _create_sync_engine(
        f"sqlite:///{_TEST_DB_PATH}",
    )


@pytest.fixture(autouse=True)
def _reset_db():
    """Drop and recreate all tables between tests for full isolation."""
    SQLModel.metadata.drop_all(_db_module.engine)
    SQLModel.metadata.create_all(_db_module.engine)
    yield


@pytest.fixture()
def client():
    """FastAPI TestClient with a clean database."""
    from main import app
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):
    """Clean up temp DB file."""
    if _TEST_DB_PATH:
        try:
            os.unlink(_TEST_DB_PATH)
        except OSError:
            pass
