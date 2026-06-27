"""Engine setup, session management, and database initialisation."""
import json
import logging
import os
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.pool import QueuePool
from sqlmodel import Session, SQLModel, create_engine, select

from core.datetime_utils import _utcnow
from core.db.encryption import encrypt_password
from core.db.models import (
    AccountModel,
    ProviderSettingModel,
    _VALID_IDENTIFIER_RE,
    _VALID_TABLES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resource monitoring
# ---------------------------------------------------------------------------


class ResourceMonitor:
    """Track system CPU and memory usage for dynamic concurrency adjustment."""

    def __init__(self, *, cpu_threshold: float = 80.0, memory_threshold: float = 85.0):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold

    def get_usage(self) -> dict:
        """Return current CPU % and memory usage %."""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
            }
        except ImportError:
            return {"cpu_percent": 0.0, "memory_percent": 0.0}

    def should_throttle(self) -> bool:
        usage = self.get_usage()
        return usage["cpu_percent"] > self.cpu_threshold or usage["memory_percent"] > self.memory_threshold

    def get_throttle_factor(self) -> float:
        """Return 0.0-1.0 factor: 1.0 = no throttle, 0.0 = full throttle."""
        usage = self.get_usage()
        cpu_factor = max(0.0, 1.0 - max(0, usage["cpu_percent"] - self.cpu_threshold) / (100 - self.cpu_threshold))
        mem_factor = max(0.0, 1.0 - max(0, usage["memory_percent"] - self.memory_threshold) / (100 - self.memory_threshold))
        return min(cpu_factor, mem_factor)


resource_monitor = ResourceMonitor()


def get_resource_metrics() -> dict:
    """Return combined resource and pool metrics for monitoring."""
    usage = resource_monitor.get_usage()
    pool_status = {}
    try:
        status = engine.pool.status()
        pool_status = {
            "checkedin": getattr(status, "checkedin", 0),
            "checkedout": getattr(status, "checkedout", 0),
            "overflow": getattr(status, "overflow", 0),
        }
    except Exception:
        pool_status = {"checkedin": 0, "checkedout": 0, "overflow": 0}
    return {
        "cpu_percent": usage["cpu_percent"],
        "memory_percent": usage["memory_percent"],
        "throttle": resource_monitor.should_throttle(),
        "throttle_factor": resource_monitor.get_throttle_factor(),
        **pool_status,
    }


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------


def _is_postgresql(url: str) -> bool:
    """Return True if *url* targets a PostgreSQL database."""
    return url.startswith("postgresql+asyncpg://") or url.startswith("postgresql://")


def _default_database_url() -> str:
    database_path = Path(__file__).resolve().parent.parent.parent / "account_manager.db"
    return f"sqlite:///{database_path}"


DATABASE_URL = os.getenv("ACCOUNT_MANAGER_DATABASE_URL", _default_database_url())


# ---------------------------------------------------------------------------
# Engine factories
# ---------------------------------------------------------------------------


def _create_sync_engine(url: str):
    """Create a synchronous engine.

    PostgreSQL URLs using the ``asyncpg`` dialect are normalised to
    ``psycopg2`` so that the sync ``Session`` wrapper works correctly.

    Connection pooling is configured with production defaults:
    QueuePool with pool_size=20, max_overflow=10, pool_recycle=3600s,
    pool_pre_ping enabled to detect stale connections.
    """
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=10,
        pool_recycle=3600,
        pool_pre_ping=True,
    )


def _create_async_engine(url: str):
    """Create an asynchronous engine (PostgreSQL only via asyncpg)."""
    from sqlalchemy.ext.asyncio import create_async_engine as _make_async

    return _make_async(url)


engine = _create_sync_engine(DATABASE_URL)


# ---------------------------------------------------------------------------
# Helpers used by migrations
# ---------------------------------------------------------------------------


def _load_json(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _accounts_columns() -> set[str]:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "accounts" not in tables:
        return set()
    return {column["name"] for column in inspector.get_columns("accounts")}


def _ensure_column(table: str, column: str, col_type: str):
    """Safely add a column to an existing table (SQLite does not support IF NOT EXISTS ADD COLUMN).

    Validates table and column names against an allowlist to prevent SQL injection.
    """
    if table not in _VALID_TABLES:
        raise ValueError(f"Invalid table name: {table!r}")
    if not _VALID_IDENTIFIER_RE.match(column):
        raise ValueError(f"Invalid column name: {column!r}")
    if not _VALID_IDENTIFIER_RE.match(col_type.split()[0]):
        raise ValueError(f"Invalid column type: {col_type!r}")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if table not in tables:
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    logger.info("Added column %s.%s", table, column)


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------


def save_account(account) -> 'AccountModel':
    """Persist base_platform.Account to database (update if same platform and email)"""
    from core.account_graph import sync_platform_account_graph

    with Session(engine) as session:
        existing = session.exec(
            select(AccountModel)
            .where(AccountModel.platform == account.platform)
            .where(AccountModel.email == account.email)
        ).first()
        if existing:
            existing.password = encrypt_password(account.password)
            existing.user_id = account.user_id or ""
            existing.updated_at = _utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            sync_platform_account_graph(session, existing, account)
            session.commit()
            return existing
        m = AccountModel(
            platform=account.platform,
            email=account.email,
            password=encrypt_password(account.password),
            user_id=account.user_id or "",
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        sync_platform_account_graph(session, m, account)
        session.commit()
        return m


def init_db():
    SQLModel.metadata.create_all(engine)
    from core.db.migrations import (
        _cleanup_empty_provider_settings,
        _cleanup_non_real_providers,
        _migrate_legacy_accounts_schema,
        _migrate_legacy_provider_keys,
    )
    from core.account_graph import sync_all_account_graphs
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository

    _migrate_legacy_accounts_schema()
    _ensure_column("provider_definitions", "category", "TEXT DEFAULT ''")
    _ensure_column("tasks", "priority", "TEXT DEFAULT 'normal'")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        ProviderDefinitionsRepository().ensure_seeded()
        _migrate_legacy_provider_keys()
        _cleanup_non_real_providers()
        _cleanup_empty_provider_settings()
        sync_all_account_graphs(session)
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
