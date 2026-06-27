"""Auth utilities for v2 API — session management and rate limiting.

Moved from api/auth.py to decouple v2 from v1 modules.
"""
from __future__ import annotations

import secrets
import time
from collections import defaultdict


# In-memory session store: token -> True
_sessions: dict[str, bool] = {}

# Rate limiting: IP -> list of timestamps
_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5 minutes


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
