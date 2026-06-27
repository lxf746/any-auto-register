"""v2 SMS provider status endpoints — HeroSMS and SmsBower provider status."""
from __future__ import annotations

from fastapi import APIRouter

from api.v2.response import ApiResponse
from core.sms.herosms import is_herosms_phone_cache_alive

router = APIRouter(prefix="/sms", tags=["sms"])


@router.get("/herosms")
def herosms_status():
    """Return HeroSMS provider status and cache info."""
    cache_alive, info = is_herosms_phone_cache_alive()
    return ApiResponse(ok=True, data={
        "provider": "herosms",
        "cache_alive": cache_alive,
        "status": "active" if cache_alive else "inactive",
        "cache_info": info,
    })


@router.get("/smsbower")
def smsbower_status():
    """Return SmsBower provider status."""
    return ApiResponse(ok=True, data={
        "provider": "smsbower",
        "status": "active",
    })
