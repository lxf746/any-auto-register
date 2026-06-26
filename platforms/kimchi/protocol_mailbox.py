"""kimchi.dev protocol registration worker.

Proven working flow:
  1. Auth0 signup via proxy → creates account
  2. tempmail.lol receives verification email
  3. Browser: goto verification ticket → auto-verifies → login page → fill form → cookie
  4. Cast.ai API key via cookie → validate
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from platforms.kimchi.core import KimchiRegister


class KimchiProtocolMailboxWorker:
    def __init__(self, *, proxy: str | None = None, log_fn: Callable[[str], None] = print):
        self.client = KimchiRegister(proxy=proxy, log_fn=log_fn)
        self.log = log_fn

    def run(
        self,
        *,
        email: str = "",
        password: str = "",
        link_callback: Callable[[], str] | None = None,
        api_key_name: str = "auto-register",
        headless: bool = True,
    ) -> dict:
        if not email or not password:
            raise RuntimeError("kimchi.dev registration requires email + password")

        result = self.client.register(
            email,
            password,
            api_key_name=api_key_name,
            verify_link_callback=link_callback,
            headless=headless,
        )

        api_key = result.get("api_key", "")
        self.log(
            f"  Registration complete: api_key={api_key[:20]}..."
            if api_key
            else "  Registration complete: no API key"
        )

        return {
            "email": result.get("email", email),
            "password": password,
            "api_key": api_key,
            "user_id": result.get("user_id", ""),
            "access_token": result.get("access_token", ""),
        }
