"""v2 API router — auth, platforms, stats, and WebSocket endpoints."""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel

from api.v2.accounts import router as accounts_router
from api.v2.actions import router as actions_router
from api.v2.auth import create_session
from api.v2.config import router as config_router
from api.v2.platform_capabilities import router as platform_capabilities_router
from api.v2.provider_definitions import router as provider_definitions_router
from api.v2.provider_settings import router as provider_settings_router
from api.v2.proxies import router as proxies_router
from api.v2.sms import router as sms_router
from api.v2.health import router as health_router
from api.v2.response import ApiResponse
from api.v2.ws import router as ws_router

router = APIRouter(tags=["v2"])
router.include_router(ws_router)
router.include_router(accounts_router)
router.include_router(health_router)
router.include_router(config_router)
router.include_router(actions_router)
router.include_router(platform_capabilities_router)
router.include_router(provider_definitions_router)
router.include_router(provider_settings_router)
router.include_router(proxies_router)
router.include_router(sms_router)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@router.get("/auth/check")
def auth_check_v2():
    """Return whether the app requires a password."""
    password = os.environ.get("APP_PASSWORD", "").strip()
    return ApiResponse(ok=True, data={"required": bool(password)})


class LoginRequest(BaseModel):
    password: str = ""


@router.post("/auth/login")
def auth_login_v2(body: LoginRequest, request: Request):
    """Authenticate with password and return a session token."""
    password = os.environ.get("APP_PASSWORD", "").strip()
    if not password:
        return ApiResponse(ok=True, data={"token": ""})

    # Rate limiting (reuse v1 logic)
    from api.v2.auth import _check_rate_limit

    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return ApiResponse(ok=False, error="Too many attempts. Try again later.")

    if hmac.compare_digest(body.password, password):
        token = create_session()
        return ApiResponse(ok=True, data={"token": token})
    return ApiResponse(ok=False, error="Incorrect password")


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

from application.platforms import PlatformsService  # noqa: E402

_platform_service = PlatformsService()


@router.get("/platforms")
def list_platforms_v2():
    """List all available platforms."""
    return ApiResponse(ok=True, data=_platform_service.list_platforms())


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

from datetime import timedelta  # noqa: E402

from sqlmodel import Session, func, select  # noqa: E402

from core.db import (  # noqa: E402
    AccountModel,
    AccountOverviewModel,
    TaskLog,
    engine,
)


@router.get("/stats/overview")
def stats_overview_v2():
    """Global overview: total registrations, success rate, account distribution."""
    with Session(engine) as session:
        total = int(
            session.exec(select(func.count()).select_from(TaskLog)).one() or 0
        )
        success = int(
            session.exec(
                select(func.count())
                .select_from(TaskLog)
                .where(TaskLog.status == "success")
            ).one()
            or 0
        )
        failed = total - success

        statuses = session.exec(
            select(
                AccountOverviewModel.lifecycle_status,
                func.count(),
            ).group_by(AccountOverviewModel.lifecycle_status)
        ).all()
        account_distribution = {row[0]: row[1] for row in statuses}

        total_accounts = int(
            session.exec(select(func.count()).select_from(AccountModel)).one() or 0
        )

    return ApiResponse(
        ok=True,
        data={
            "total_registrations": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "total_accounts": total_accounts,
            "account_distribution": account_distribution,
        },
    )


# ---------------------------------------------------------------------------
# Accounts (v2 wrapper)
# ---------------------------------------------------------------------------

from application.accounts import AccountsService  # noqa: E402
from domain.accounts import AccountQuery  # noqa: E402

_service = AccountsService()


@router.get("/accounts")
def list_accounts_v2(
    platform: str = "",
    status: str = "",
    email: str = "",
    page: int = 1,
    page_size: int = 20,
):
    """List accounts with v2 envelope."""
    result = _service.list_accounts(
        AccountQuery(platform=platform, status=status, email=email, page=page, page_size=page_size)
    )
    return ApiResponse(ok=True, data=result)
