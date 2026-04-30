import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.account_checks import router as account_checks_router
from api.accounts import router as accounts_router
from api.actions import router as actions_router
from api.auth import router as auth_router
from api.config import router as config_router
from core.auth import AuthMiddleware
from api.health import router as health_router
from api.lifecycle import router as lifecycle_router
from api.platform_capabilities import router as platform_capabilities_router
from api.platforms import router as platforms_router
from api.provider_definitions import router as provider_definitions_router
from api.provider_settings import router as provider_settings_router
from api.proxies import router as proxies_router
from api.sms import router as sms_router
from api.stats import router as stats_router
from api.system import router as system_router
from api.task_commands import router as task_commands_router
from api.task_logs import router as task_logs_router
from api.tasks import router as tasks_router
from core.db import init_db
from core.registry import load_all
from providers.registry import load_all as load_providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    load_all()
    load_providers()
    print("[OK] 数据库初始化完成")
    from core.registry import list_platforms
    print(f"[OK] 已加载平台: {[p['name'] for p in list_platforms()]}")
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


app = FastAPI(title="Account Manager", version="2.0.0", lifespan=lifespan)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts_router, prefix="/api")
app.include_router(account_checks_router, prefix="/api")
app.include_router(actions_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(lifecycle_router, prefix="/api")
app.include_router(platforms_router, prefix="/api")
app.include_router(platform_capabilities_router, prefix="/api")
app.include_router(provider_definitions_router, prefix="/api")
app.include_router(provider_settings_router, prefix="/api")
app.include_router(proxies_router, prefix="/api")
app.include_router(sms_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(task_commands_router, prefix="/api")
app.include_router(task_logs_router, prefix="/api")
app.include_router(system_router, prefix="/api")


_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        return FileResponse(os.path.join(_static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
