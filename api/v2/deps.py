"""Shared dependencies for v2 API endpoints."""
from __future__ import annotations

from api.auth import validate_session


def get_current_user(token: str | None) -> str | None:
    """Validate a bearer token and return it if valid, else None."""
    if token and validate_session(token):
        return token
    return None
