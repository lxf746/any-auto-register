"""TLS helper utilities.

Default behavior: TLS verification is ENABLED.
Use insecure_request() or mark_session_insecure() only when explicitly needed.
"""
from __future__ import annotations

import logging
import warnings
from contextlib import contextmanager
from typing import Any

from urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(__name__)


@contextmanager
def suppress_insecure_request_warning():
    """Suppress urllib3 TLS warnings only when certificate verification is explicitly disabled."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InsecureRequestWarning)
        yield


def insecure_request(request_callable, *args, **kwargs) -> Any:
    """Execute requests with verify=False and suppress corresponding warnings.

    WARNING: Disabling TLS verification makes the connection vulnerable to
    MITM attacks. Use only when absolutely necessary and log a warning.
    """
    logger.warning("TLS verification disabled — connection is vulnerable to MITM attacks")
    kwargs.setdefault("verify", False)
    with suppress_insecure_request_warning():
        return request_callable(*args, **kwargs)


def mark_session_insecure(session: Any) -> Any:
    """
    Mark requests.Session as verify=False and use with suppress_insecure_request_warning on the caller side.
    Returns session for chaining.

    WARNING: Disabling TLS verification makes the connection vulnerable to
    MITM attacks. Use only when absolutely necessary.
    """
    logger.warning("TLS verification disabled for session — connection is vulnerable to MITM attacks")
    session.verify = False
    return session

