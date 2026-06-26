from __future__ import annotations

import time
from datetime import datetime, timezone


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    """Return current UTC datetime as ISO string."""
    return _utcnow().isoformat().replace("+00:00", "Z")


def _utcnow_ts() -> int:
    """Return current UTC timestamp as integer."""
    return int(time.time())


def ensure_utc_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def serialize_datetime(value: datetime | str | None) -> str | None:
    normalized = ensure_utc_datetime(value)
    if normalized is None:
        return None
    return normalized.isoformat().replace("+00:00", "Z")


def format_local_clock(value: datetime | str | None, fmt: str = "%H:%M:%S") -> str:
    normalized = ensure_utc_datetime(value)
    if normalized is None:
        return ""
    return normalized.astimezone().strftime(fmt)
