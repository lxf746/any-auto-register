from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session

from core.db import engine
from core.registry import list_platforms
from services.solver_manager import is_running


class HealthRuntime:
    def health(self) -> dict:
        return {"ok": True, "service": "account-manager-v2"}

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
            registry_ok = platform_count > 0
            if not registry_ok:
                registry_error = "no platform plugins loaded"
        except Exception as exc:
            platforms = []
            platform_count = 0
            registry_error = str(exc)

        return {
            "ok": db_ok and registry_ok,
            "database": {"ok": db_ok, "error": db_error},
            "registry": {"ok": registry_ok, "platform_count": platform_count, "error": registry_error},
            "solver": {"running": is_running()},
        }
