"""v2 Provider definitions endpoints — CRUD and driver templates for provider types."""
from __future__ import annotations

from fastapi import APIRouter, Request

from api.v2.response import ApiResponse
from application.provider_definitions import ProviderDefinitionsService

router = APIRouter(prefix="/providers", tags=["providers"])

_service = ProviderDefinitionsService()


@router.get("/{provider_type}")
def list_definitions(provider_type: str):
    """List provider definitions by type."""
    result = _service.list_definitions(provider_type)
    return ApiResponse(ok=True, data=result)


@router.get("/{provider_type}/drivers")
def list_driver_templates(provider_type: str):
    """List driver templates for a provider type."""
    result = _service.list_driver_templates(provider_type)
    return ApiResponse(ok=True, data=result)


@router.post("/{provider_type}")
async def save_definition(provider_type: str, request: Request):
    """Create or update a provider definition."""
    body = await request.json()
    body["provider_type"] = provider_type
    result = _service.save_definition(body)
    return ApiResponse(ok=True, data=result)


@router.delete("/{provider_type}/{definition_id}")
def delete_definition(provider_type: str, definition_id: int):
    """Delete a provider definition."""
    result = _service.delete_definition(definition_id)
    return ApiResponse(ok=True, data=result)
