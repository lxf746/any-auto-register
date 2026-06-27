"""v2 Health endpoints — readiness, pool status, and rate limits."""
from __future__ import annotations

from fastapi import APIRouter

from api.v2.response import ApiResponse
from application.health import HealthService

router = APIRouter(prefix="/health", tags=["health"])

_service = HealthService()


@router.get("/")
def health_check():
    """Return basic health status."""
    result = _service.health()
    return ApiResponse(ok=True, data=result)


@router.get("/ready")
def readiness_check():
    """Return readiness status with database, registry, solver checks."""
    result = _service.readiness()
    return ApiResponse(ok=True, data=result)


@router.get("/pools")
def pool_status():
    """Return database, HTTP, and browser pool metrics."""
    result = _service.pool_status()
    return ApiResponse(ok=True, data=result)


@router.get("/rate-limits")
def rate_limit_status():
    """Return rate limit metrics."""
    result = _service.rate_limit_status()
    return ApiResponse(ok=True, data=result)
