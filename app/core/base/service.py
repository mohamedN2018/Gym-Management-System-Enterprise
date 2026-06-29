"""Service base class.

Services own *all* business logic, validation orchestration, permission checks, transactions
and event publication (Part 2). This base provides the cross-cutting plumbing every service
shares so concrete services stay focused on rules:

- structured logging (injected; falls back to the stdlib logger by class name)
- event publication helper
- :class:`Result` factories
- :meth:`_guard` — runs risky work, turning any exception into a failed ``Result`` and logging
  it, so a service method *never crashes the application* (Part 1).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol, TypeVar, runtime_checkable

from app.core.errors import AppError, ErrorCode
from app.core.events import Event, EventBus
from app.core.result import Error, Result

T = TypeVar("T")


@runtime_checkable
class LoggerLike(Protocol):
    """Structural type satisfied by both ``logging.Logger`` and the app ``LoggingService``."""

    def debug(self, msg: str, *args: object, **kwargs: object) -> None: ...
    def info(self, msg: str, *args: object, **kwargs: object) -> None: ...
    def warning(self, msg: str, *args: object, **kwargs: object) -> None: ...
    def error(self, msg: str, *args: object, **kwargs: object) -> None: ...
    def exception(self, msg: str, *args: object, **kwargs: object) -> None: ...


class BaseService:
    """Common base for application services."""

    def __init__(
        self,
        *,
        logger: LoggerLike | None = None,
        events: EventBus | None = None,
    ) -> None:
        self._logger: LoggerLike = logger or logging.getLogger(type(self).__module__)
        self._events = events

    # --- result helpers ---------------------------------------------------
    @staticmethod
    def _ok(value: T = None) -> Result[T]:  # type: ignore[assignment]
        return Result.ok(value)

    @staticmethod
    def _fail(error: Error | AppError | str, code: ErrorCode = ErrorCode.UNKNOWN) -> Result:
        return Result.fail(error, code)

    # --- events -----------------------------------------------------------
    def _publish(self, event: Event) -> None:
        if self._events is not None:
            self._events.publish(event)

    # --- exception boundary ----------------------------------------------
    def _guard(self, action: Callable[[], T], *, message: str) -> Result[T]:
        """Execute ``action`` and convert failures into a failed :class:`Result`.

        Known :class:`AppError`\\ s are surfaced verbatim (they are already UI-safe). Any other
        exception is logged with a traceback and replaced by a generic infrastructure error so
        internal details never leak to the UI.
        """
        try:
            return Result.ok(action())
        except AppError as exc:
            log = self._logger.warning if exc.is_operational else self._logger.error
            log("%s: %s", message, exc)
            return Result.fail(exc)
        except Exception as exc:
            self._logger.exception("%s (unexpected error)", message)
            return Result.fail(
                Error.of(message, ErrorCode.INFRASTRUCTURE, cause=type(exc).__name__)
            )
