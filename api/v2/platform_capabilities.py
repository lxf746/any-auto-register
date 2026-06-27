"""v2 Platform capabilities endpoints — list, update, and reset platform capabilities."""
from __future__ import annotations

from fastapi import APIRouter, Request

from api.v2.response import ApiResponse
from application.platform_capabilities import PlatformCapabilitiesService

router = APIRouter(prefix="/platforms", tags=["platforms"])

_service = PlatformCapabilitiesService()


@router.get("/")
def list_platforms():
    """List all platforms with their capabilities."""
    result = _service.list_platforms()
    return ApiResponse(ok=True, data=result)


@router.put("/{name}/capabilities")
async def update_capabilities(name: str, request: Request):
    """Update platform capabilities."""
    body = await request.json()
    result = _service.update(name, body)
    return ApiResponse(ok=True, data=result)


@router.delete("/{name}/capabilities")
def reset_capabilities(name: str):
    """Reset platform capabilities to defaults."""
    result = _service.reset(name)
    return ApiResponse(ok=True, data=result)
