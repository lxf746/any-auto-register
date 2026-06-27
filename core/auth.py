"""Simple bearer-token authentication middleware.

Set the environment variable ``APP_PASSWORD`` (or config key ``app_password``)
to enable password protection.  When set, every API request must carry either:

  - Header ``Authorization: Bearer <session_token>``
  - Cookie ``_auth=<session_token>``

Session tokens are generated on login via ``api.auth.create_session`` and
validated against the in-memory session store.

The health / ready endpoints are always public so that Docker health-checks
work without credentials.
"""
from __future__ import annotations

import os

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

_PUBLIC_PREFIXES = ("/api/health", "/api/ready", "/api/auth/", "/api/v2/auth/")


def _get_password() -> str:
    return os.environ.get("APP_PASSWORD", "").strip()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        password = _get_password()
        if not password:
            return await call_next(request)

        path = request.url.path
        # Public endpoints & static assets
        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)
        if not path.startswith("/api"):
            return await call_next(request)

        # Check Authorization header for session token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            from api.v2.auth import validate_session
            token = auth_header[7:]
            if validate_session(token):
                return await call_next(request)

        # Check cookie for session token
        cookie_token = request.cookies.get("_auth")
        if cookie_token:
            from api.v2.auth import validate_session
            if validate_session(cookie_token):
                return await call_next(request)

        return Response(content='{"detail":"Unauthorized"}', status_code=401, media_type="application/json")
