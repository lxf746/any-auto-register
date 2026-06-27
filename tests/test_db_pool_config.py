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

    def test_pool_overflow_is_0_initially(self):
        from core.db.engine import engine
        assert engine.pool.overflow() == 0, f"Expected overflow=0, got {engine.pool.overflow()}"

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
