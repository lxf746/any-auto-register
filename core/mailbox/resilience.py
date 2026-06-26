"""Mailbox resilience components — health checks, circuit breaker, rate limiting, dedup."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    enabled: bool = True
    timeout: int = 10
    cache_ttl: int = 300  # seconds


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiting."""
    enabled: bool = True
    requests_per_minute: int = 30


@dataclass
class ResilienceConfig:
    """Combined resilience configuration."""
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    rate_limiter: RateLimiterConfig = field(default_factory=RateLimiterConfig)
    email_dedup_enabled: bool = True


class HealthCheck:
    """Pre-flight health check with TTL-based caching."""

    def __init__(self, config: HealthCheckConfig | None = None):
        self.config = config or HealthCheckConfig()
        self._cache: dict[str, tuple[bool, float]] = {}  # key -> (result, timestamp)

    def check(self, key: str, check_fn: Callable[[], bool]) -> bool:
        """Run health check with caching."""
        if not self.config.enabled:
            return True

        now = time.time()
        if key in self._cache:
            result, ts = self._cache[key]
            if now - ts < self.config.cache_ttl:
                return result

        try:
            result = check_fn()
            self._cache[key] = (result, now)
            return result
        except Exception as exc:
            logger.warning("Health check failed for %s: %s", key, exc)
            self._cache[key] = (False, now)
            return False

    def invalidate(self, key: str) -> None:
        """Invalidate cached health check result."""
        self._cache.pop(key, None)


class CircuitBreaker:
    """Circuit breaker with closed/open/half-open states."""

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker opened after %d failures", self._failure_count)

    def allow_request(self) -> bool:
        """Check if a request is allowed."""
        if not self.config.enabled:
            return True

        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True  # Allow one probe request
        return False


class RateLimiter:
    """Per-provider rate limiting using sliding window."""

    def __init__(self, config: RateLimiterConfig | None = None):
        self.config = config or RateLimiterConfig()
        self._timestamps: list[float] = []

    def allow(self) -> bool:
        """Check if a request is allowed under rate limit."""
        if not self.config.enabled:
            return True

        now = time.time()
        window_start = now - 60  # 1 minute window

        # Remove old timestamps
        self._timestamps = [t for t in self._timestamps if t > window_start]

        if len(self._timestamps) >= self.config.requests_per_minute:
            return False

        self._timestamps.append(now)
        return True


class EmailDedup:
    """Email deduplication cache to prevent creating duplicates."""

    def __init__(self, ttl: int = 300):
        self._cache: dict[str, float] = {}  # email -> timestamp
        self._ttl = ttl

    def is_duplicate(self, email: str) -> bool:
        """Check if email was recently created."""
        now = time.time()
        self._cleanup(now)

        if email in self._cache:
            return True

        self._cache[email] = now
        return False

    def _cleanup(self, now: float) -> None:
        """Remove expired entries."""
        expired = [k for k, v in self._cache.items() if now - v > self._ttl]
        for k in expired:
            del self._cache[k]
