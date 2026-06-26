from __future__ import annotations

import hmac
import os
import secrets

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory session store: token -> True
_sessions: dict[str, bool] = {}


class LoginRequest(BaseModel):
    password: str = ""


def create_session() -> str:
    """Generate a cryptographically secure session token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = True
    return token


def validate_session(token: str) -> bool:
    """Check if a session token is valid."""
    return token in _sessions


def destroy_session(token: str) -> None:
    """Invalidate a session token."""
    _sessions.pop(token, None)


@router.get("/check")
def auth_check():
    """Return whether the app requires a password."""
    password = os.environ.get("APP_PASSWORD", "").strip()
    return {"required": bool(password)}


@router.post("/login")
def auth_login(body: LoginRequest):
    password = os.environ.get("APP_PASSWORD", "").strip()
    if not password:
        return {"ok": True}
    if hmac.compare_digest(body.password, password):
        token = create_session()
        return {"ok": True, "token": token}
    return {"ok": False, "error": "Incorrect password"}
