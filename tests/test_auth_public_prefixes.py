"""Tests for core/auth.py _PUBLIC_PREFIXES after v1 removal.

Verifies that:
- v1 prefix "/api/auth/" is removed from _PUBLIC_PREFIXES
- v2 prefix "/api/v2/auth/" is preserved
- infrastructure prefixes are preserved
"""

from core.auth import _PUBLIC_PREFIXES


def test_public_prefixes_has_v2_auth():
    """v2 auth prefix must be present."""
    assert "/api/v2/auth/" in _PUBLIC_PREFIXES


def test_public_prefixes_has_health():
    """Health endpoint must remain public."""
    assert "/api/health" in _PUBLIC_PREFIXES


def test_public_prefixes_has_ready():
    """Ready endpoint must remain public."""
    assert "/api/ready" in _PUBLIC_PREFIXES


def test_v1_auth_prefix_removed():
    """v1 auth prefix '/api/auth/' must NOT be in _PUBLIC_PREFIXES."""
    assert "/api/auth/" not in _PUBLIC_PREFIXES


def test_v1_auth_subpath_not_public():
    """A v1-style auth path must not match any prefix."""
    v1_path = "/api/auth/some-path"
    assert not any(v1_path.startswith(p) for p in _PUBLIC_PREFIXES)


def test_v2_auth_subpath_is_public():
    """A v2-style auth path must match a prefix."""
    v2_path = "/api/v2/auth/check"
    assert any(v2_path.startswith(p) for p in _PUBLIC_PREFIXES)
