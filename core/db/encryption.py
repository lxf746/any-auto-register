"""Fernet encryption helpers for password storage at rest."""
import base64
import hashlib
import os
import threading

_FERNET = None
_fernet_lock = threading.Lock()


def _get_fernet():
    """Lazy-init Fernet cipher from ACCOUNT_ENCRYPTION_KEY env var."""
    global _FERNET
    with _fernet_lock:
        if _FERNET is not None:
            return _FERNET
        from cryptography.fernet import Fernet

        raw_key = os.getenv("ACCOUNT_ENCRYPTION_KEY", "")
        if not raw_key:
            # Derive a deterministic key from a passphrase (not truly secure for
            # production, but better than plaintext; set ACCOUNT_ENCRYPTION_KEY
            # in production).
            raw_key = hashlib.pbkdf2_hmac(
                "sha256",
                b"any-auto-register-default-key",
                b"any-auto-register-salt",
                100_000,
            )
            key = base64.urlsafe_b64encode(raw_key)
        else:
            key = base64.urlsafe_b64encode(
                hashlib.pbkdf2_hmac("sha256", raw_key.encode(), b"any-auto-register-salt", 100_000)
            )
        _FERNET = Fernet(key)
        return _FERNET


def encrypt_password(plaintext: str) -> str:
    """Encrypt a password for storage. Returns base64-encoded ciphertext."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a stored password. Handles both encrypted and legacy plaintext."""
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # Legacy plaintext — return as-is
        return ciphertext
