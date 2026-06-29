"""Railway-oriented :class:`Result` type.

Services return ``Result[T]`` so callers (controllers/UI) get an explicit success/failure
outcome without ``try/except`` at every boundary, and the application *never crashes* on an
operational error (Part 1). Infrastructure code may still raise :class:`AppError`; the
service base wraps those into a failed ``Result``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from app.core.errors import AppError, ErrorCode

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True, slots=True)
class Error:
    """Immutable, UI-safe description of a failure carried by a failed :class:`Result`."""

    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_app_error(cls, exc: AppError) -> Error:
        return cls(code=exc.code, message=exc.message, details=dict(exc.details))

    @classmethod
    def of(
        cls,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        **details: Any,
    ) -> Error:
        return cls(code=code, message=message, details=details)

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"


class Result(Generic[T]):
    """Outcome of an operation: either a value (success) or an :class:`Error` (failure).

    Construct via :meth:`ok` / :meth:`fail`. Treat instances as immutable.
    """

    __slots__ = ("_error", "_value")

    def __init__(self, value: T | None, error: Error | None) -> None:
        # Internal constructor; prefer the ``ok``/``fail`` factories.
        self._value = value
        self._error = error

    # --- factories --------------------------------------------------------
    @classmethod
    def ok(cls, value: T = None) -> Result[T]:  # type: ignore[assignment]
        return cls(value, None)

    @classmethod
    def fail(cls, error: Error | AppError | str, code: ErrorCode = ErrorCode.UNKNOWN) -> Result[T]:
        if isinstance(error, Error):
            err = error
        elif isinstance(error, AppError):
            err = Error.from_app_error(error)
        else:
            err = Error.of(str(error), code)
        return cls(None, err)

    # --- state ------------------------------------------------------------
    @property
    def is_success(self) -> bool:
        return self._error is None

    @property
    def is_failure(self) -> bool:
        return self._error is not None

    @property
    def value(self) -> T:
        """Return the success value, or raise ``ValueError`` if this is a failure."""
        if self._error is not None:
            raise ValueError(f"Cannot read value from a failed Result: {self._error}")
        return self._value  # type: ignore[return-value]

    @property
    def error(self) -> Error | None:
        return self._error

    # --- combinators ------------------------------------------------------
    def unwrap_or(self, default: T) -> T:
        """Return the value on success, otherwise ``default``."""
        return self._value if self._error is None else default  # type: ignore[return-value]

    def map(self, fn: Callable[[T], U]) -> Result[U]:
        """Transform the success value; failures pass through unchanged."""
        if self._error is not None:
            return Result(None, self._error)
        return Result.ok(fn(self._value))  # type: ignore[arg-type]

    def and_then(self, fn: Callable[[T], Result[U]]) -> Result[U]:
        """Chain another ``Result``-returning operation (monadic bind)."""
        if self._error is not None:
            return Result(None, self._error)
        return fn(self._value)  # type: ignore[arg-type]

    def __bool__(self) -> bool:
        return self.is_success

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        if self._error is not None:
            return f"Result.fail({self._error!r})"
        return f"Result.ok({self._value!r})"
