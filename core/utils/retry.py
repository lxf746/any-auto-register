"""Retry and backoff utilities with linear and exponential strategies."""
import time
import random
import logging
from typing import Callable, Any, TypeVar
from functools import wraps

T = TypeVar("T")


def _compute_sleep(
    backoff_factor: float,
    attempt: int,
    strategy: str,
    jitter: bool,
) -> float:
    """Compute sleep duration based on strategy and attempt number."""
    if strategy == "exponential":
        delay = backoff_factor * (2 ** attempt)
    else:
        # Linear (default) — backward compatible
        delay = backoff_factor * (attempt + 1)

    if jitter:
        delay += random.uniform(0, 1)

    return delay


def retry(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
    backoff_strategy: str = "linear",
    jitter: bool = False,
) -> Callable:
    """Decorator for retrying function calls with backoff.

    Parameters
    ----------
    backoff_strategy:
        ``"linear"`` (default) uses ``factor * (attempt + 1)``.
        ``"exponential"`` uses ``factor * 2 ** attempt``.
    jitter:
        When *True*, adds a random 0-1 s offset to the sleep time to
        prevent thundering-herd effects.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        if on_retry:
                            on_retry(attempt + 1, e)
                        time.sleep(
                            _compute_sleep(backoff_factor, attempt, backoff_strategy, jitter)
                        )
            raise last_exception
        return wrapper
    return decorator


def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
    backoff_strategy: str = "linear",
    jitter: bool = False,
) -> T:
    """Function-style retry (not decorator).

    Accepts the same ``backoff_strategy`` and ``jitter`` parameters as
    :func:`retry`.
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                if on_retry:
                    on_retry(attempt + 1, e)
                time.sleep(
                    _compute_sleep(backoff_factor, attempt, backoff_strategy, jitter)
                )
    raise last_exception
