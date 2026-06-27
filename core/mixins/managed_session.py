"""Managed HTTP session lifecycle mixin."""
import threading
from typing import Any


class ManagedSession:
    """Mixin providing lazy session init, close(), and context manager support."""

    _session: Any = None
    _session_lock: threading.Lock = threading.Lock()

    def _create_session(self) -> Any:
        """Create a new session. Subclasses must override."""
        raise NotImplementedError

    def _get_session(self) -> Any:
        """Get or create session (thread-safe)."""
        if self._session is not None:
            return self._session
        with self._session_lock:
            if self._session is None:
                self._session = self._create_session()
            return self._session

    def close(self) -> None:
        """Close the session."""
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
