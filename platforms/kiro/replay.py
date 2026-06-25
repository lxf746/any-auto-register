"""Kiro session replay — save tokens to disk, reuse for Q&A without re-registration."""

from __future__ import annotations

import json
import os
from typing import Any

from platforms.kiro.switch import send_kiro_message, load_session_messages
from platforms.kiro.event_stream import iter_aws_event_stream


DEFAULT_TOKEN_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "KiroSession",
    "tokens.json",
)


def save_tokens(tokens: dict, path: str = "") -> str:
    """Save Kiro session tokens to a JSON file on disk.

    Accepts the result dict from ``KiroProtocolMailboxWorker.run()``
    or ``KiroRegister.register()``.

    Returns the path written to.
    """
    out = path or DEFAULT_TOKEN_PATH
    os.makedirs(os.path.dirname(out), exist_ok=True)
    data = {
        "accessToken": tokens.get("accessToken", ""),
        "sessionToken": tokens.get("sessionToken", ""),
        "csrfToken": tokens.get("csrfToken", ""),
        "userId": tokens.get("userId", ""),
        "email": tokens.get("email", ""),
        "name": tokens.get("name", ""),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return out


def load_tokens(path: str = "") -> dict[str, str] | None:
    """Load Kiro session tokens from disk. Returns None if no saved session."""
    src = path or DEFAULT_TOKEN_PATH
    if not os.path.isfile(src):
        return None
    try:
        with open(src, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def clear_tokens(path: str = "") -> None:
    """Delete saved tokens from disk."""
    src = path or DEFAULT_TOKEN_PATH
    if os.path.isfile(src):
        os.remove(src)


# ──────────────────────────────────────────────
#  High-level replay client
# ──────────────────────────────────────────────


class KiroSession:
    """Reusable Kiro Q&A session backed by saved tokens.

    Usage::

        session = KiroSession()
        if not session.load():
            # register first, then session.save(result_dict)
            ...
        print(session.ask("Write a Python hello world function"))
        for ev in session.history():
            print(ev)
    """

    def __init__(self, token_path: str = ""):
        self._path = token_path or DEFAULT_TOKEN_PATH
        self.access_token: str = ""
        self.session_token: str = ""
        self.csrf_token: str = ""
        self.user_id: str = ""
        self._space_id: str = ""
        self._session_id: str = ""

    # ── persistence ──────────────────────────────

    @property
    def has_tokens(self) -> bool:
        return bool(self.access_token and self.session_token and self.user_id)

    def save(self, result: dict) -> str:
        save_tokens(result, self._path)
        self.access_token = result.get("accessToken", "")
        self.session_token = result.get("sessionToken", "")
        self.csrf_token = result.get("csrfToken", "")
        self.user_id = result.get("userId", "")
        return self._path

    def load(self) -> bool:
        data = load_tokens(self._path)
        if data is None:
            return False
        self.access_token = data.get("accessToken", "")
        self.session_token = data.get("sessionToken", "")
        self.csrf_token = data.get("csrfToken", "")
        self.user_id = data.get("userId", "")
        return self.has_tokens

    def clear(self) -> None:
        clear_tokens(self._path)
        self.access_token = ""
        self.session_token = ""
        self.csrf_token = ""
        self.user_id = ""

    # ── Q&A ──────────────────────────────────────

    def ask(self, prompt: str, *, timeout: int = 120) -> str:
        """Send a prompt and return the full assistant response text."""
        if not self.has_tokens:
            raise RuntimeError("No tokens loaded. Call load() or save() first.")
        return send_kiro_message(
            prompt,
            access_token=self.access_token,
            session_token=self.session_token,
            user_id=self.user_id,
            csrf_token=self.csrf_token,
            space_id=self._space_id,
            session_id=self._session_id,
            timeout=timeout,
        )

    def history(self, *, timeout: int = 30) -> list[dict]:
        """Load conversation history for the current session."""
        if not self.has_tokens or not self._space_id or not self._session_id:
            return []
        return load_session_messages(
            self._space_id, self._session_id,
            access_token=self.access_token,
            session_token=self.session_token,
            user_id=self.user_id,
            csrf_token=self.csrf_token,
            timeout=timeout,
        )

    def set_space(self, space_id: str, session_id: str) -> None:
        self._space_id = space_id
        self._session_id = session_id

    @property
    def space_id(self) -> str:
        return self._space_id

    @property
    def session_id(self) -> str:
        return self._session_id or self._space_id
