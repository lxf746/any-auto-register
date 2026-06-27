"""v2 Account endpoints — CRUD, stats, and import."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.v2.response import ApiResponse
from application.accounts import AccountsService
from domain.accounts import (
    AccountCreateCommand,
    AccountImportLine,
    AccountQuery,
    AccountUpdateCommand,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])

_service = AccountsService()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AccountCreateRequest(BaseModel):
    platform: str
    email: str
    password: str
    user_id: str = ""
    lifecycle_status: str = "registered"
    overview: dict = {}
    credentials: dict = {}
    provider_accounts: list[dict] = []
    provider_resources: list[dict] = []
    primary_token: str = ""
    cashier_url: str = ""
    region: str = ""
    trial_end_time: int = 0


class AccountUpdateRequest(BaseModel):
    password: Optional[str] = None
    user_id: Optional[str] = None
    lifecycle_status: Optional[str] = None
    overview: Optional[dict] = None
    credentials: Optional[dict] = None
    provider_accounts: Optional[list[dict]] = None
    provider_resources: Optional[list[dict]] = None
    replace_provider_accounts: bool = False
    replace_provider_resources: bool = False
    primary_token: Optional[str] = None
    cashier_url: Optional[str] = None
    region: Optional[str] = None
    trial_end_time: Optional[int] = None


class AccountImportRequest(BaseModel):
    platform: str
    lines: list[str]


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.post("/")
def create_account(body: AccountCreateRequest):
    """Create a new account."""
    command = AccountCreateCommand(
        platform=body.platform,
        email=body.email,
        password=body.password,
        user_id=body.user_id,
        lifecycle_status=body.lifecycle_status,
        overview=body.overview,
        credentials=body.credentials,
        provider_accounts=body.provider_accounts,
        provider_resources=body.provider_resources,
        primary_token=body.primary_token,
        cashier_url=body.cashier_url,
        region=body.region,
        trial_end_time=body.trial_end_time,
    )
    result = _service.create_account(command)
    return ApiResponse(ok=True, data=result)


@router.get("/{account_id}")
def get_account(account_id: int):
    """Get a single account by ID."""
    result = _service.get_account(account_id)
    if result is None:
        raise HTTPException(404, "Account not found")
    return ApiResponse(ok=True, data=result)


@router.patch("/{account_id}")
def update_account(account_id: int, body: AccountUpdateRequest):
    """Update an existing account."""
    command = AccountUpdateCommand(
        password=body.password,
        user_id=body.user_id,
        lifecycle_status=body.lifecycle_status,
        overview=body.overview,
        credentials=body.credentials,
        provider_accounts=body.provider_accounts,
        provider_resources=body.provider_resources,
        replace_provider_accounts=body.replace_provider_accounts,
        replace_provider_resources=body.replace_provider_resources,
        primary_token=body.primary_token,
        cashier_url=body.cashier_url,
        region=body.region,
        trial_end_time=body.trial_end_time,
    )
    result = _service.update_account(account_id, command)
    if result is None:
        raise HTTPException(404, "Account not found")
    return ApiResponse(ok=True, data=result)


@router.delete("/{account_id}")
def delete_account(account_id: int):
    """Delete an account."""
    result = _service.delete_account(account_id)
    return ApiResponse(ok=True, data={"ok": True})


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/stats")
def account_stats():
    """Return account statistics."""
    result = _service.get_stats()
    return ApiResponse(ok=True, data=result)


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


@router.post("/import")
def import_accounts(body: AccountImportRequest):
    """Import accounts from text lines."""
    result = _service.import_accounts(body.platform, body.lines)
    return ApiResponse(ok=True, data=result)
