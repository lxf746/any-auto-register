"""Tests for database connection pool configuration (POOL-01)."""
import pytest
from sqlalchemy.pool import QueuePool


class TestMainEnginePoolConfig:
    """Verify core/db/engine.py QueuePool settings."""

    def test_pool_is_queue_pool(self):
        from core.db.engine import engine
        assert isinstance(engine.pool, QueuePool), f"Expected QueuePool, got {type(engine.pool)}"

    def test_pool_size_is_20(self):
        from core.db.engine import engine
        assert engine.pool.size() == 20, f"Expected pool_size=20, got {engine.pool.size()}"

    def test_pool_overflow_is_bounded(self):
        from core.db.engine import engine
        # overflow() returns current_overflow (checkedout - pool_size).
        # Must not exceed max_overflow=10.
        assert engine.pool.overflow() <= 10, f"Overflow {engine.pool.overflow()} exceeds max_overflow=10"

    def test_pool_recycle_is_3600(self):
        from core.db.engine import engine
        assert engine.pool._recycle == 3600, f"Expected pool_recycle=3600, got {engine.pool._recycle}"

    def test_pool_pre_ping_enabled(self):
        from core.db.engine import engine
        assert engine.pool._pre_ping is True, f"Expected pool_pre_ping=True, got {engine.pool._pre_ping}"


class TestCustomerPortalEnginePoolConfig:
    """Verify customer_portal_api/app/db.py QueuePool settings."""

    def test_portal_pool_is_queue_pool(self):
        from customer_portal_api.app.db import engine
        assert isinstance(engine.pool, QueuePool), f"Expected QueuePool, got {type(engine.pool)}"

    def test_portal_pool_size_is_20(self):
        from customer_portal_api.app.db import engine
        assert engine.pool.size() == 20, f"Expected pool_size=20, got {engine.pool.size()}"

    def test_portal_pool_recycle_is_3600(self):
        from customer_portal_api.app.db import engine
        assert engine.pool._recycle == 3600, f"Expected pool_recycle=3600, got {engine.pool._recycle}"

    def test_portal_pool_pre_ping_enabled(self):
        from customer_portal_api.app.db import engine
        assert engine.pool._pre_ping is True, f"Expected pool_pre_ping=True, got {engine.pool._pre_ping}"


class TestPoolConfigSource:
    """Verify the source code has correct pool kwargs (regardless of runtime DB)."""

    def test_engine_source_has_queue_pool_kwargs(self):
        """The source code for _create_sync_engine must include QueuePool config."""
        import inspect
        from core.db.engine import _create_sync_engine
        source = inspect.getsource(_create_sync_engine)
        assert "poolclass=QueuePool" in source, "Missing poolclass=QueuePool in _create_sync_engine"
        assert "pool_size=20" in source, "Missing pool_size=20 in _create_sync_engine"
        assert "max_overflow=10" in source, "Missing max_overflow=10 in _create_sync_engine"
        assert "pool_recycle=3600" in source, "Missing pool_recycle=3600 in _create_sync_engine"
        assert "pool_pre_ping=True" in source, "Missing pool_pre_ping=True in _create_sync_engine"

    def test_portal_source_has_queue_pool_kwargs(self):
        """The source code for customer portal must include QueuePool config."""
        import inspect
        from customer_portal_api import app as app_mod
        source = inspect.getsource(app_mod.db)
        assert "poolclass=QueuePool" in source, "Missing poolclass=QueuePool in portal db.py"
        assert "pool_size=20" in source, "Missing pool_size=20 in portal db.py"
        assert "pool_recycle=3600" in source, "Missing pool_recycle=3600 in portal db.py"
        assert "pool_pre_ping=True" in source, "Missing pool_pre_ping=True in portal db.py"
