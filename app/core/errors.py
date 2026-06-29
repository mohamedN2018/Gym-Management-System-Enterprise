"""Typed application error hierarchy.

Every layer raises :class:`AppError` (or a subclass) instead of leaking framework/ORM
exceptions. Errors carry a stable machine-readable :class:`ErrorCode`, a human-readable
message, structured ``details``, and an ``is_operational`` flag that the global handler uses
to decide between graceful recovery (operational) and crash-logging (programmer/infra bugs).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Stable, machine-readable error categories. Values are persisted in logs/audit."""

    UNKNOWN = "UNKNOWN"
    VALIDATION = "VALIDATION"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    AUTHENTICATION = "AUTHENTICATION"
    BUSINESS_RULE = "BUSINESS_RULE"
    CONCURRENCY = "CONCURRENCY"
    DATABASE = "DATABASE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    CONFIGURATION = "CONFIGURATION"


class AppError(Exception):
    """Base class for all application errors.

    Args:
        message: Human-readable, end-user-safe message.
        code: Machine-readable :class:`ErrorCode`; defaults to the subclass' ``default_code``.
        details: Structured context (field errors, ids, …). Never include secrets.
        cause: The underlying exception, if any (preserved for logging, not surfaced to UI).
        is_operational: ``True`` for expected/handled conditions; ``False`` for bugs.
    """

    default_code: ErrorCode = ErrorCode.UNKNOWN
    default_operational: bool = True

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | None = None,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
        is_operational: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details: dict[str, Any] = details or {}
        self.cause = cause
        self.is_operational = self.default_operational if is_operational is None else is_operational
        if cause is not None:
            self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging/IPC (never includes the raw cause/traceback)."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "is_operational": self.is_operational,
        }

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"{type(self).__name__}(code={self.code.value!r}, message={self.message!r}, "
            f"details={self.details!r})"
        )


class ValidationError(AppError):
    """Input failed validation. ``details`` maps field name -> list[str] of messages."""

    default_code = ErrorCode.VALIDATION


class NotFoundError(AppError):
    """A requested entity does not exist (or is soft-deleted and not requested)."""

    default_code = ErrorCode.NOT_FOUND


class ConflictError(AppError):
    """A uniqueness/state conflict (duplicate membership number, already checked-in, …)."""

    default_code = ErrorCode.CONFLICT


class PermissionDeniedError(AppError):
    """The current actor lacks the permission required for the action."""

    default_code = ErrorCode.PERMISSION_DENIED


class AuthenticationError(AppError):
    """Credentials are missing or invalid."""

    default_code = ErrorCode.AUTHENTICATION


class BusinessRuleError(AppError):
    """A domain invariant/business rule was violated."""

    default_code = ErrorCode.BUSINESS_RULE


class ConcurrencyError(AppError):
    """Optimistic-locking conflict: the record changed since it was read."""

    default_code = ErrorCode.CONCURRENCY


class DatabaseError(AppError):
    """Persistence failure. Not operational: indicates infra/programmer fault."""

    default_code = ErrorCode.DATABASE
    default_operational = False


class InfrastructureError(AppError):
    """Failure in an external/OS resource (filesystem, printer, camera, …)."""

    default_code = ErrorCode.INFRASTRUCTURE
    default_operational = False


class ConfigurationError(AppError):
    """Invalid or missing configuration. Not operational."""

    default_code = ErrorCode.CONFIGURATION
    default_operational = False
