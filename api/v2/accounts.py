"""v2 Account endpoints — CRUD, stats, import, export, and checks."""
from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.v2.response import ApiResponse
from application.account_checks import AccountChecksService
from application.account_exports import AccountExportsService, ExportArtifact
from application.accounts import AccountsService
from domain.accounts import (
    AccountCreateCommand,
    AccountExportSelection,
    AccountImportLine,
    AccountQuery,
    AccountUpdateCommand,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])

_service = AccountsService()
_exports_service = AccountExportsService()
_checks_service = AccountChecksService()


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
# Stats & Import (defined BEFORE /{account_id} to avoid route shadowing)
# ---------------------------------------------------------------------------


@router.get("/stats")
def account_stats():
    """Return account statistics."""
    result = _service.get_stats()
    return ApiResponse(ok=True, data=result)


@router.post("/import")
def import_accounts(body: AccountImportRequest):
    """Import accounts from text lines."""
    result = _service.import_accounts(body.platform, body.lines)
    return ApiResponse(ok=True, data=result)


# ---------------------------------------------------------------------------
# Export request model
# ---------------------------------------------------------------------------


class AccountExportRequest(BaseModel):
    platform: str = ""
    ids: list[int] = []
    select_all: bool = False
    status_filter: str = ""
    search_filter: str = ""


def _stream_artifact(artifact: ExportArtifact) -> StreamingResponse:
    """Convert an ExportArtifact to a StreamingResponse."""
    if isinstance(artifact.content, io.BytesIO):
        def iter_bytes():
            yield artifact.content.read()
        content_iter = iter_bytes()
    elif isinstance(artifact.content, bytes):
        def iter_bytes():
            yield artifact.content
        content_iter = iter_bytes()
    else:
        def iter_str():
            yield artifact.content.encode("utf-8")
        content_iter = iter_str()

    headers = {"Content-Disposition": f'attachment; filename="{artifact.filename}"'}
    return StreamingResponse(content_iter, media_type=artifact.media_type, headers=headers)


def _to_selection(body: AccountExportRequest) -> AccountExportSelection:
    return AccountExportSelection(
        platform=body.platform,
        ids=body.ids,
        select_all=body.select_all,
        status_filter=body.status_filter,
        search_filter=body.search_filter,
    )


# ---------------------------------------------------------------------------
# Export endpoints (defined BEFORE /{account_id} to avoid route shadowing)
# ---------------------------------------------------------------------------


@router.post("/export/csv")
def export_csv(body: AccountExportRequest):
    """Export accounts as CSV file."""
    selection = _to_selection(body)
    artifact = _exports_service.export_chatgpt_csv(selection)
    return _stream_artifact(artifact)


@router.post("/export/json")
def export_json(body: AccountExportRequest):
    """Export accounts as JSON file."""
    selection = _to_selection(body)
    artifact = _exports_service.export_chatgpt_json(selection)
    return _stream_artifact(artifact)


@router.post("/export/sub2api")
def export_sub2api(body: AccountExportRequest):
    """Export accounts as Sub2API format."""
    selection = _to_selection(body)
    artifact = _exports_service.export_chatgpt_sub2api(selection)
    return _stream_artifact(artifact)


@router.post("/export/cpa")
def export_cpa(body: AccountExportRequest):
    """Export accounts as CPA token format."""
    selection = _to_selection(body)
    artifact = _exports_service.export_chatgpt_cpa(selection)
    return _stream_artifact(artifact)


@router.post("/export/kiro-go")
def export_kiro_go(body: AccountExportRequest):
    """Export Kiro accounts as Kiro-Go config."""
    selection = _to_selection(body)
    artifact = _exports_service.export_kiro_go(selection)
    return _stream_artifact(artifact)


@router.post("/export/any2api")
def export_any2api(body: AccountExportRequest):
    """Export accounts as Any2API admin config."""
    selection = _to_selection(body)
    artifact = _exports_service.export_any2api(selection)
    return _stream_artifact(artifact)


# ---------------------------------------------------------------------------
# Check endpoints (defined BEFORE /{account_id} to avoid route shadowing)
# ---------------------------------------------------------------------------


@router.post("/check-all")
def check_all(platform: str = ""):
    """Trigger async check for all accounts."""
    result = _checks_service.check_all_async(platform)
    return ApiResponse(ok=True, data=result)


@router.post("/check-one/{account_id}")
def check_one(account_id: int):
    """Trigger async check for one account."""
    result = _checks_service.check_one_async(account_id)
    if result is None:
        raise HTTPException(404, "Account not found")
    return ApiResponse(ok=True, data=result)


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
    if not result.get("ok"):
        raise HTTPException(404, "Account not found")
    return ApiResponse(ok=True, data={"ok": True})
