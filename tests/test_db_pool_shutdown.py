"""Tests for engine.dispose() on application shutdown (POOL-01)."""
import pytest


class TestEngineDisposeOnShutdown:
    """Verify engine.dispose() is called during shutdown paths."""

    def test_engine_dispose_is_callable(self):
        from core.db.engine import engine
        # dispose() must be callable and idempotent
        engine.dispose()
        engine.dispose()  # second call must not raise

    def test_lifecycle_manager_stop_disposes_engine(self):
        """LifecycleManager.stop() must call engine.dispose()."""
        import inspect
        from core.lifecycle import LifecycleManager
        source = inspect.getsource(LifecycleManager.stop)
        assert "dispose()" in source, "LifecycleManager.stop() must call engine.dispose()"

    def test_main_lifespan_disposes_engine(self):
        """main.py lifespan shutdown block must call engine.dispose()."""
        import inspect
        from main import lifespan
        source = inspect.getsource(lifespan)
        assert "dispose()" in source, "main.py lifespan must call engine.dispose()"
