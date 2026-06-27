"""v2 Config endpoints — configuration management."""
from __future__ import annotations

from fastapi import APIRouter, Request

from api.v2.response import ApiResponse
from application.config import ConfigService

router = APIRouter(prefix="/config", tags=["config"])

_service = ConfigService()


@router.get("/")
def get_config():
    """Return filtered config key-value pairs."""
    result = _service.get_config()
    return ApiResponse(ok=True, data=result)


@router.get("/options")
def get_options():
    """Return platform choices, provider definitions, and settings."""
    result = _service.get_options()
    return ApiResponse(ok=True, data=result)


@router.put("/")
async def update_config(request: Request):
    """Update allowed config keys."""
    body = await request.json()
    updated = body.get("data", body)
    result = _service.update_config(updated)
    return ApiResponse(ok=True, data=result)
