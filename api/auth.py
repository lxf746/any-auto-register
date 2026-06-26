from __future__ import annotations

import hmac
import os
import secrets
import time
from collections import defaultdict

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory session store: token -> True
_sessions: dict[str, bool] = {}

# Rate limiting: IP -> list of timestamps
_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5 minutes


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


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if rate limited."""
    now = time.time()
    cutoff = now - _WINDOW_SECONDS
    _login_attempts[ip] = [t for t in _login_attempts[ip] if t > cutoff]
    if len(_login_attempts[ip]) >= _MAX_ATTEMPTS:
        return False
    _login_attempts[ip].append(now)
    return True


@router.get("/check")
def auth_check():
    """Return whether the app requires a password."""
    password = os.environ.get("APP_PASSWORD", "").strip()
    return {"required": bool(password)}


@router.post("/login")
def auth_login(body: LoginRequest, request: Request):
    password = os.environ.get("APP_PASSWORD", "").strip()
    if not password:
        return {"ok": True}

    # Rate limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return {"ok": False, "error": "Too many attempts. Try again later."}

    if hmac.compare_digest(body.password, password):
        token = create_session()
        return {"ok": True, "token": token}
    return {"ok": False, "error": "Incorrect password"}
