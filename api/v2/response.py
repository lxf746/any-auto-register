"""Unified API response envelope for v2 endpoints."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """Standard response wrapper returned by all v2 endpoints."""

    ok: bool
    data: Any = None
    error: Optional[str] = None
