"""Centralized logging service.

Two channels:

1. **Diagnostic log** (``logs/gym_erp.log`` + console) — human-readable application events,
   warnings and errors.
2. **Audit log** (``logs/audit.log``) — append-only JSON lines, one per audited business action,
   carrying the fields mandated by Part 1 (timestamp, user, module, action, old/new value,
   device, result, execution time).

Both handlers are **append-only**: the application never deletes logs automatically (Part 1).
Operator-driven archival/rotation is handled by the (later) Database Maintenance tooling.
"""

from __future__ import annotations

import json
import logging
import socket
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.constants import APP_SLUG
from app.core.events import Event
from app.settings.paths import AppPaths

_DIAGNOSTIC_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_AUDIT_LOGGER_NAME = f"{APP_SLUG}.audit"
#: Marker attribute identifying handlers installed by this service (for idempotent re-config).
_OWNED_FLAG = "_gym_erp_owned"


def _mark_owned(handler: logging.Handler) -> None:
    setattr(handler, _OWNED_FLAG, True)


def _purge_owned_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, _OWNED_FLAG, False):
            logger.removeHandler(handler)
            handler.close()


class _JsonLineFormatter(logging.Formatter):
    """Render the ``audit`` extra payload as a single compact JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = getattr(record, "audit", None) or {"message": record.getMessage()}
        return json.dumps(payload, ensure_ascii=False, default=str)


class LoggingService:
    """Owns logging configuration and the audit trail. One instance per process."""

    def __init__(self) -> None:
        self._configured = False
        self._device = socket.gethostname()
        self._audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)

    # --- configuration ----------------------------------------------------
    def configure(
        self, *, paths: AppPaths, level: str = "INFO", console: bool = True
    ) -> LoggingService:
        """Install file/console handlers.

        Idempotent across instances: any handlers previously installed by this service are
        removed first, so re-bootstrapping (e.g. in tests) never duplicates handlers.
        """
        if self._configured:
            return self

        paths.logs_dir.mkdir(parents=True, exist_ok=True)
        root = logging.getLogger()
        root.setLevel(level.upper())
        _purge_owned_handlers(root)
        _purge_owned_handlers(self._audit_logger)

        formatter = logging.Formatter(_DIAGNOSTIC_FORMAT)

        file_handler = logging.FileHandler(paths.log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        _mark_owned(file_handler)
        root.addHandler(file_handler)

        # Only attach a console handler when a real stderr stream exists. In a windowed
        # (no-console) packaged build, sys.stderr is None and a StreamHandler would fail.
        if console and sys.stderr is not None:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            _mark_owned(console_handler)
            root.addHandler(console_handler)

        # Audit: dedicated append-only JSON file, isolated from the diagnostic root.
        audit_handler = logging.FileHandler(paths.audit_log_file, encoding="utf-8")
        audit_handler.setFormatter(_JsonLineFormatter())
        _mark_owned(audit_handler)
        self._audit_logger.setLevel(logging.INFO)
        self._audit_logger.addHandler(audit_handler)
        self._audit_logger.propagate = False

        self._configured = True
        return self

    # --- accessors --------------------------------------------------------
    def get_logger(self, name: str) -> logging.Logger:
        """Return a namespaced diagnostic logger (e.g. for a service or module)."""
        return logging.getLogger(name)

    # --- audit trail ------------------------------------------------------
    def audit(
        self,
        *,
        action: str,
        module: str,
        result: str = "success",
        user: str | int | None = None,
        old_value: Any = None,
        new_value: Any = None,
        execution_ms: float | None = None,
        **extra: Any,
    ) -> None:
        """Append one structured entry to the audit trail."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user": user,
            "module": module,
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
            "device": self._device,
            "result": result,
            "execution_ms": execution_ms,
        }
        if extra:
            entry.update(extra)
        self._audit_logger.info("audit", extra={"audit": entry})

    # --- event bus error sink --------------------------------------------
    def on_event_handler_error(self, event: Event, exc: BaseException) -> None:
        """Sink wired into :class:`~app.core.events.EventBus` so listener faults are logged."""
        logging.getLogger(f"{APP_SLUG}.events").error(
            "Event handler failed for %r: %s", event.name, exc, exc_info=exc
        )
