from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session

from core.db import engine
from core.registry import list_platforms
from core.rate_limiter import rate_limit_metrics, _platform_limiters, _provider_limiters
from services.solver_manager import is_running


class HealthRuntime:
    def health(self) -> dict:
        return {"ok": True, "service": "account-manager-v2"}

    def pool_status(self) -> dict:
        """Return connection pool metrics for monitoring."""
        from core.mixins.managed_session import ManagedSession

        # DB pool metrics (per D-04)
        db_pool = engine.pool
        db_status = {
            "size": db_pool.size(),
            "checked_in": db_pool.checkedin(),
            "checked_out": db_pool.checkedout(),
            "overflow": db_pool.overflow(),
            "status": db_pool.status(),
        }

        # HTTP session metrics
        http_sessions = {
            "active_count": ManagedSession._session_count,
        }

        # Browser pool metrics (if available)
        browser_pool: dict = {"available": False}
        try:
            from services.solver_manager import is_running as _is_running
            if _is_running():
                # Solver is a separate process — expose basic availability flag
                browser_pool = {"available": True, "status": "external_process"}
        except Exception:
            pass

        return {
            "database": db_status,
            "http": http_sessions,
            "browser": browser_pool,
        }

    def rate_limit_status(self) -> dict:
        """Return rate limit metrics for monitoring."""
        return {
            "metrics": rate_limit_metrics.get_metrics(),
            "active_platform_limiters": len(_platform_limiters),
            "active_provider_limiters": len(_provider_limiters),
        }

    def readiness(self) -> dict:
        db_ok = False
        db_error = ""
        registry_ok = False
        registry_error = ""
        try:
            with Session(engine) as session:
                session.exec(text("SELECT 1"))
            db_ok = True
        except Exception as exc:
            db_error = str(exc)

        try:
            platforms = list_platforms()
            platform_count = len(platforms)
            registry_ok = True
        except Exception as exc:
            platforms = []
            platform_count = 0
            registry_error = str(exc)

        return {
            "ok": db_ok and registry_ok,
            "database": {"ok": db_ok, "error": db_error},
            "registry": {"ok": registry_ok, "platform_count": platform_count, "error": registry_error},
            "solver": {"running": is_running()},
            "pool": self.pool_status(),
        }
