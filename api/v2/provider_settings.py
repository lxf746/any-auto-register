"""v2 Provider settings endpoints — CRUD and catalog for provider settings."""
from __future__ import annotations

from fastapi import APIRouter, Request

from api.v2.response import ApiResponse
from application.provider_settings import ProviderSettingsService

router = APIRouter(prefix="/provider-settings", tags=["provider-settings"])

_service = ProviderSettingsService()


@router.get("/catalog")
def get_catalog():
    """Return catalog options with captcha policy."""
    result = _service.get_catalog_options()
    return ApiResponse(ok=True, data=result)


@router.get("/{provider_type}")
def list_settings(provider_type: str):
    """List provider settings by type."""
    result = _service.list_settings(provider_type)
    return ApiResponse(ok=True, data=result)


@router.post("/{provider_type}")
async def save_setting(provider_type: str, request: Request):
    """Create or update a provider setting."""
    body = await request.json()
    body["provider_type"] = provider_type
    result = _service.save_setting(body)
    return ApiResponse(ok=True, data=result)


@router.delete("/{provider_type}/{setting_id}")
def delete_setting(provider_type: str, setting_id: int):
    """Delete a provider setting."""
    result = _service.delete_setting(setting_id)
    return ApiResponse(ok=True, data=result)
