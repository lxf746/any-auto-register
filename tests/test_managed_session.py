"""Tests for ManagedSession mixin applied to ProtocolExecutor, HTTPClient, and platform clients."""
import pytest
from unittest.mock import MagicMock, patch
from core.mixins.managed_session import ManagedSession
from core.executors.protocol import ProtocolExecutor
from core.http_client import HTTPClient


class TestManagedSessionMixin:
    """Verify ManagedSession mixin works correctly."""

    def test_managed_session_is_abstract(self):
        """ManagedSession._create_session raises NotImplementedError."""
        ms = ManagedSession()
        with pytest.raises(NotImplementedError):
            ms._create_session()

    def test_managed_session_lazy_init(self):
        """_get_session() calls _create_session only once."""
        mock_session = MagicMock()
        call_count = 0

        class FakeClient(ManagedSession):
            def _create_session(self):
                nonlocal call_count
                call_count += 1
                return mock_session

        client = FakeClient()
        s1 = client._get_session()
        s2 = client._get_session()
        assert s1 is mock_session
        assert s2 is mock_session
        assert call_count == 1

    def test_managed_session_close_resets(self):
        """close() sets _session to None, next _get_session creates new."""
        call_count = 0

        class FakeClient(ManagedSession):
            def _create_session(self):
                nonlocal call_count
                call_count += 1
                return MagicMock()

        client = FakeClient()
        s1 = client._get_session()
        client.close()
        s2 = client._get_session()
        assert s1 is not s2
        assert call_count == 2

    def test_managed_session_context_manager(self):
        """ManagedSession works as context manager."""
        class FakeClient(ManagedSession):
            def _create_session(self):
                return MagicMock()

        with FakeClient() as client:
            client._get_session()
        # After exiting context, session should be closed


class TestProtocolExecutorManagedSession:
    """ProtocolExecutor should inherit ManagedSession."""

    def test_inherits_managed_session(self):
        assert issubclass(ProtocolExecutor, ManagedSession)

    def test_close_works(self):
        """ProtocolExecutor.close() should not raise."""
        pe = ProtocolExecutor()
        pe.close()  # Should not raise

    def test_session_lazy(self):
        """ProtocolExecutor creates session lazily via _get_session."""
        pe = ProtocolExecutor()
        # Session is created on first _get_session() call
        session = pe._get_session()
        assert session is not None
        pe.close()

    def test_close_sets_session_none(self):
        """After close(), _get_session creates new session."""
        pe = ProtocolExecutor()
        s1 = pe._get_session()
        pe.close()
        s2 = pe._get_session()
        assert s1 is not s2
        pe.close()


class TestHTTPClientManagedSession:
    """HTTPClient should inherit ManagedSession."""

    def test_inherits_managed_session(self):
        assert issubclass(HTTPClient, ManagedSession)

    def test_close_works(self):
        """HTTPClient.close() should not raise."""
        hc = HTTPClient()
        hc.close()

    def test_close_sets_session_none(self):
        """After close(), _session is None."""
        hc = HTTPClient()
        _ = hc.session  # trigger lazy init
        hc.close()
        assert hc._session is None


class TestPlatformClientsManagedSession:
    """Platform clients should inherit ManagedSession."""

    def test_windsurf_client_inherits(self):
        from platforms.windsurf.core import WindsurfClient
        assert issubclass(WindsurfClient, ManagedSession)

    def test_windsurf_client_close(self):
        from platforms.windsurf.core import WindsurfClient
        client = WindsurfClient()
        client.close()

    def test_blink_register_inherits(self):
        from platforms.blink.core import BlinkRegister
        assert issubclass(BlinkRegister, ManagedSession)

    def test_blink_register_close(self):
        from platforms.blink.core import BlinkRegister
        client = BlinkRegister()
        client.close()

    def test_openblocklabs_inherits(self):
        from platforms.openblocklabs.core import OpenBlockLabsRegister
        assert issubclass(OpenBlockLabsRegister, ManagedSession)

    def test_openblocklabs_close(self):
        from platforms.openblocklabs.core import OpenBlockLabsRegister
        client = OpenBlockLabsRegister()
        client.close()
