"""Rate limiting infrastructure — per-platform, per-provider, and metrics."""
from __future__ import annotations

import time
from typing import ClassVar

# ---------------------------------------------------------------------------
# Default limits (D-01 / D-02 from CONTEXT.md)
# ---------------------------------------------------------------------------
PLATFORM_DEFAULTS: dict[str, int] = {
    "chatgpt": 10,
    "windsurf": 5,
    "kimchi": 3,
}
PLATFORM_FALLBACK = 5

PROVIDER_DEFAULTS: dict[str, int] = {
    "sms": 10,
    "captcha": 5,
}


# ---------------------------------------------------------------------------
# Platform rate limiter
# ---------------------------------------------------------------------------
class PlatformRateLimiter:
    """Per-platform rate limiting using a sliding window (same algorithm as
    :class:`core.mailbox.resilience.RateLimiter`)."""

    def __init__(self, platform: str, requests_per_minute: int | None = None):
        if requests_per_minute is None:
            requests_per_minute = PLATFORM_DEFAULTS.get(platform, PLATFORM_FALLBACK)
        self._platform = platform
        self._requests_per_minute = requests_per_minute
        self._timestamps: list[float] = []

    def allow(self) -> bool:
        """Return *True* if a new request is allowed under the sliding window."""
        now = time.time()
        window_start = now - 60

        # Remove old timestamps outside the 60-second window
        self._timestamps = [t for t in self._timestamps if t > window_start]

        if len(self._timestamps) >= self._requests_per_minute:
            return False

        self._timestamps.append(now)
        return True

    def wait_time(self) -> float:
        """Seconds until the next request is allowed (0.0 if allowed now)."""
        now = time.time()
        window_start = now - 60
        self._timestamps = [t for t in self._timestamps if t > window_start]

        if len(self._timestamps) < self._requests_per_minute:
            return 0.0

        oldest = self._timestamps[0]
        return max(0.0, oldest + 60 - now)

    def reset(self) -> None:
        """Clear all recorded timestamps (useful in tests)."""
        self._timestamps.clear()


# ---------------------------------------------------------------------------
# Provider rate limiter
# ---------------------------------------------------------------------------
class ProviderRateLimiter:
    """Per-provider rate limiting for SMS / captcha providers."""

    def __init__(
        self,
        provider_type: str,
        provider_name: str,
        requests_per_minute: int | None = None,
    ):
        if requests_per_minute is None:
            requests_per_minute = PROVIDER_DEFAULTS.get(provider_type, 10)
        self._provider_type = provider_type
        self._provider_name = provider_name
        self._requests_per_minute = requests_per_minute
        self._timestamps: list[float] = []

    def allow(self) -> bool:
        now = time.time()
        window_start = now - 60
        self._timestamps = [t for t in self._timestamps if t > window_start]

        if len(self._timestamps) >= self._requests_per_minute:
            return False

        self._timestamps.append(now)
        return True

    def wait_time(self) -> float:
        now = time.time()
        window_start = now - 60
        self._timestamps = [t for t in self._timestamps if t > window_start]

        if len(self._timestamps) < self._requests_per_minute:
            return 0.0

        oldest = self._timestamps[0]
        return max(0.0, oldest + 60 - now)

    def reset(self) -> None:
        self._timestamps.clear()


# ---------------------------------------------------------------------------
# Rate limit metrics
# ---------------------------------------------------------------------------
class RateLimitMetrics:
    """Centralised rate-limit observability — tracks hits, current usage, and
    throttle events per limiter key."""

    def __init__(self) -> None:
        self._hits: dict[str, int] = {}
        self._usage: dict[str, list[float]] = {}
        self._throttles: dict[str, int] = {}

    def record_hit(self, key: str) -> None:
        """Increment the denial (hit) counter for *key*."""
        self._hits[key] = self._hits.get(key, 0) + 1

    def record_throttle(self, key: str) -> None:
        """Increment the throttle-event counter for *key*."""
        self._throttles[key] = self._throttles.get(key, 0) + 1

    def record_usage(self, key: str) -> None:
        """Append a timestamp to the usage list for *key* and clean up entries
        older than 60 seconds."""
        now = time.time()
        window_start = now - 60

        if key not in self._usage:
            self._usage[key] = []

        self._usage[key].append(now)
        self._usage[key] = [t for t in self._usage[key] if t > window_start]

    def get_metrics(self) -> dict:
        """Return a snapshot of all metrics.

        ``usage`` values are lists of recent timestamps (last 60 s); use
        ``len()`` to get the count.
        """
        now = time.time()
        window_start = now - 60
        usage_recent: dict[str, list[float]] = {}
        for k, timestamps in self._usage.items():
            usage_recent[k] = [t for t in timestamps if t > window_start]

        return {
            "hits": dict(self._hits),
            "usage": usage_recent,
            "throttles": dict(self._throttles),
        }

    def reset(self) -> None:
        """Clear all counters (useful in tests)."""
        self._hits.clear()
        self._usage.clear()
        self._throttles.clear()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
rate_limit_metrics = RateLimitMetrics()

# ---------------------------------------------------------------------------
# Singleton registries for helper functions
# ---------------------------------------------------------------------------
_platform_limiters: dict[str, PlatformRateLimiter] = {}
_provider_limiters: dict[str, ProviderRateLimiter] = {}


def check_platform_limit(
    platform: str,
    metrics: RateLimitMetrics | None = None,
) -> bool:
    """Convenience helper — creates / reuses a :class:`PlatformRateLimiter`
    for *platform*, calls :meth:`allow`, and optionally records metrics."""
    if platform not in _platform_limiters:
        _platform_limiters[platform] = PlatformRateLimiter(platform)

    limiter = _platform_limiters[platform]
    allowed = limiter.allow()
    key = f"platform:{platform}"

    if metrics is not None:
        metrics.record_usage(key)
        if not allowed:
            metrics.record_hit(key)

    return allowed


def check_provider_limit(
    provider_type: str,
    provider_name: str,
    metrics: RateLimitMetrics | None = None,
) -> bool:
    """Convenience helper — creates / reuses a :class:`ProviderRateLimiter`
    and calls :meth:`allow`."""
    composite_key = f"{provider_type}:{provider_name}"
    if composite_key not in _provider_limiters:
        _provider_limiters[composite_key] = ProviderRateLimiter(
            provider_type, provider_name
        )

    limiter = _provider_limiters[composite_key]
    allowed = limiter.allow()
    key = composite_key

    if metrics is not None:
        metrics.record_usage(key)
        if not allowed:
            metrics.record_hit(key)

    return allowed
