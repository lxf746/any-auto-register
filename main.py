import os
import sys
from contextlib import asynccontextmanager

# Force stdout/stderr to utf-8 (Windows Chinese edition defaults to gbk, and ✗ ✓ etc.
# non-GBK characters throw UnicodeEncodeError and crash the process). errors="replace" as fallback,
# any encoding failures are replaced with ? instead of throwing.
# Also set PYTHONUTF8 environment variable so child processes use UTF-8.
os.environ.setdefault("PYTHONUTF8", "1")
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# Fallback: if reconfigure is unavailable (some PyInstaller versions), wrap it
if sys.stdout is not None and getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
if sys.stderr is not None and getattr(sys.stderr, "encoding", "").lower() not in ("utf-8", "utf8"):
    try:
        import io
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v2.router import router as v2_router
from core.auth import AuthMiddleware
from core.db import init_db
from core.registry import load_all
from providers.registry import load_all as load_providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    load_all()
    load_providers()
    print("[OK] Database initialized")
    from core.registry import list_platforms
    print(f"[OK] Loaded platforms: {[p['name'] for p in list_platforms()]}")
    from core.scheduler import scheduler
    scheduler.start()
    from services.task_runtime import task_runtime
    task_runtime.start()
    from services.solver_manager import start_async
    start_async()
    from core.lifecycle import lifecycle_manager
    lifecycle_manager.start()
    yield
    from core.lifecycle import lifecycle_manager as _lifecycle_manager
    _lifecycle_manager.stop()
    from core.scheduler import scheduler as _scheduler
    _scheduler.stop()
    from services.task_runtime import task_runtime as _task_runtime
    _task_runtime.stop()
    from services.solver_manager import stop
    stop()
    # Dispose DB pool — idempotent, safe even if lifecycle_manager already disposed it
    from core.db import engine as _engine
    _engine.dispose()


app = FastAPI(title="Account Manager", version="2.0.0", lifespan=lifespan)

# CORS: restrict to specific origins via CORS_ORIGINS env var (comma-separated).
# Default: only allow same-origin requests (no cross-origin).
_cors_origins_raw = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()] if _cors_origins_raw else []

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# v2 API — versioned endpoints with unified response envelope
app.include_router(v2_router, prefix="/api/v2")





if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
