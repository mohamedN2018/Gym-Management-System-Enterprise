"""Symmetric encryption for sensitive settings and fields.

Uses Fernet (AES-128-CBC + HMAC-SHA256, with authenticated tokens). The key lives locally in
the app data directory so the application works fully offline; it is created with owner-only
permissions on first run and is included in secure backups (Part 1/2). Losing the key means
encrypted values cannot be recovered — this is documented in the operator runbook.
"""

from __future__ import annotations

import contextlib
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import InfrastructureError


class EncryptionService:
    """Encrypts/decrypts UTF-8 strings using a Fernet key."""

    def __init__(self, key: bytes) -> None:
        try:
            self._fernet = Fernet(key)
        except (ValueError, TypeError) as exc:
            raise InfrastructureError("Invalid encryption key.", cause=exc) from exc

    @staticmethod
    def generate_key() -> bytes:
        return Fernet.generate_key()

    @classmethod
    def from_key_file(cls, path: str | os.PathLike[str]) -> EncryptionService:
        """Load the key at ``path``, generating and persisting one if it does not exist."""
        key_path = Path(path)
        if key_path.exists():
            key = key_path.read_bytes().strip()
        else:
            key = cls.generate_key()
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_bytes(key)
            _restrict_permissions(key_path)
        return cls(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string, returning a URL-safe token."""
        if plaintext is None:  # type: ignore[unreachable]
            raise InfrastructureError("Cannot encrypt None.")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Decrypt a token produced by :meth:`encrypt`."""
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise InfrastructureError(
                "Failed to decrypt value (wrong key or corrupt data).", cause=exc
            ) from exc


def _restrict_permissions(path: Path) -> None:
    """Best-effort: restrict the key file to the owner (no-op where unsupported).

    On some Windows configurations ``chmod`` is a partial no-op; ACL hardening is handled by
    the installer. Startup must never fail over key-file permissions.
    """
    with contextlib.suppress(OSError, NotImplementedError):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
