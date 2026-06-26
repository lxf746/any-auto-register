from __future__ import annotations

import os
import sys


class Settings:
    app_name: str = os.getenv("PORTAL_APP_NAME", "Customer Portal API")
    app_version: str = "0.2.0"
    jwt_secret: str = os.getenv("PORTAL_JWT_SECRET", "")
    access_token_ttl_seconds: int = int(os.getenv("PORTAL_ACCESS_TOKEN_TTL_SECONDS", "7200"))
    refresh_token_ttl_seconds: int = int(os.getenv("PORTAL_REFRESH_TOKEN_TTL_SECONDS", str(30 * 24 * 3600)))
    seed_admin_username: str = os.getenv("PORTAL_ADMIN_USERNAME", "")
    seed_admin_password: str = os.getenv("PORTAL_ADMIN_PASSWORD", "")
    seed_admin_email: str = os.getenv("PORTAL_ADMIN_EMAIL", "")
    cors_origins: list[str] = [item.strip() for item in os.getenv("PORTAL_CORS_ORIGINS", "*").split(",") if item.strip()]


def _validate_settings(settings: Settings) -> None:
    """Fail fast if critical secrets are missing or default."""
    errors: list[str] = []

    if not settings.jwt_secret:
        errors.append(
            "PORTAL_JWT_SECRET is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    if not settings.seed_admin_username:
        errors.append("PORTAL_ADMIN_USERNAME is not set.")

    if not settings.seed_admin_password:
        errors.append("PORTAL_ADMIN_PASSWORD is not set.")

    if errors:
        print("[FATAL] Configuration errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)


settings = Settings()
_validate_settings(settings)
