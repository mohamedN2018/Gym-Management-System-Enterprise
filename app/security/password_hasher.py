"""Password hashing with argon2id.

Passwords are never stored in plaintext (Part 1). argon2id is the current OWASP-recommended
algorithm; parameters are owned by argon2-cffi defaults (tuned for interactive logins) and can
be migrated transparently via :meth:`needs_rehash`.
"""

from __future__ import annotations

from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import Argon2Error, InvalidHashError, VerifyMismatchError

from app.core.errors import ValidationError


class PasswordHasher:
    """Hashes and verifies passwords. Stateless and thread-safe."""

    def __init__(self) -> None:
        self._hasher = _Argon2Hasher()

    def hash(self, password: str) -> str:
        """Return an argon2id hash string. Raises :class:`ValidationError` if blank."""
        if not password:
            raise ValidationError(
                "Password must not be empty.", details={"fields": {"password": ["required"]}}
            )
        return self._hasher.hash(password)

    def verify(self, hashed: str, password: str) -> bool:
        """Return ``True`` iff ``password`` matches ``hashed``.

        Any verification failure — mismatch, malformed/corrupt stored hash — returns ``False``
        (fail closed) rather than raising, so authentication logic stays simple and safe.
        """
        if not hashed or not password:
            return False
        try:
            return self._hasher.verify(hashed, password)
        except (VerifyMismatchError, InvalidHashError, Argon2Error):
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Return whether ``hashed`` should be re-computed (parameters upgraded)."""
        try:
            return self._hasher.check_needs_rehash(hashed)
        except (InvalidHashError, Argon2Error):
            return True
