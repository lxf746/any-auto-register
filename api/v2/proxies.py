"""v2 Proxies endpoints — CRUD, bulk, toggle, check, and scan for proxies."""
from __future__ import annotations

from fastapi import APIRouter, Request

from api.v2.response import ApiResponse
from application.proxies import ProxiesService
from domain.proxies import ProxyBulkCreateCommand, ProxyCreateCommand

router = APIRouter(prefix="/proxies", tags=["proxies"])

_service = ProxiesService()


# ---------------------------------------------------------------------------
# Static routes (defined BEFORE /{proxy_id} to avoid route shadowing)
# ---------------------------------------------------------------------------


@router.get("/")
def list_proxies():
    """List all proxies."""
    result = _service.list_proxies()
    return ApiResponse(ok=True, data=result)


@router.post("/")
async def create_proxy(request: Request):
    """Create a proxy."""
    body = await request.json()
    command = ProxyCreateCommand(url=body["url"], region=body.get("region", ""))
    result = _service.create_proxy(command)
    return ApiResponse(ok=True, data=result)


@router.post("/bulk")
async def bulk_create_proxies(request: Request):
    """Create multiple proxies."""
    body = await request.json()
    command = ProxyBulkCreateCommand(proxies=body["proxies"], region=body.get("region", ""))
    result = _service.bulk_create_proxies(command)
    return ApiResponse(ok=True, data=result)


@router.post("/check")
def trigger_check():
    """Trigger proxy health check."""
    result = _service.trigger_check()
    return ApiResponse(ok=True, data=result)


@router.post("/scan")
async def scan_proxies(request: Request):
    """Scan for public proxies."""
    body = await request.json()
    result = _service.scan_public_proxies(
        target_count=body.get("target_count", 10),
        test_timeout=body.get("test_timeout", 10),
        region=body.get("region", "public"),
    )
    return ApiResponse(ok=True, data=result)


# ---------------------------------------------------------------------------
# Parameterized routes (after static routes to avoid shadowing)
# ---------------------------------------------------------------------------


@router.delete("/{proxy_id}")
def delete_proxy(proxy_id: int):
    """Delete a proxy."""
    result = _service.delete_proxy(proxy_id)
    return ApiResponse(ok=True, data=result)


@router.post("/{proxy_id}/toggle")
def toggle_proxy(proxy_id: int):
    """Toggle proxy active state."""
    result = _service.toggle_proxy(proxy_id)
    return ApiResponse(ok=True, data=result)
