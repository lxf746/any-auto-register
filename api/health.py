from __future__ import annotations

from fastapi import APIRouter

from application.health import HealthService

router = APIRouter(tags=["health"])
service = HealthService()


@router.get("/health")
def health():
    return service.health()


@router.get("/ready")
def ready():
    return service.readiness()


@router.get("/pools")
def pools():
    """Dedicated pool metrics endpoint for monitoring."""
    return service.pool_status()


@router.get("/rate-limits")
def rate_limits():
    """Rate limit metrics for monitoring."""
    return service.rate_limit_status()
