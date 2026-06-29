"""In-process publish/subscribe event bus.

Modules stay decoupled by communicating through events instead of importing each other
(Part 2: *modules listen to events; never directly call unrelated modules*). The bus is
synchronous and thread-safe. Handler exceptions never propagate to the publisher: they are
routed to an injectable error sink (wired to the logging service at bootstrap) so one bad
listener cannot break an unrelated workflow or crash the app.
"""

from __future__ import annotations

import contextlib
import threading
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

#: A subscriber callback. Receives the published :class:`Event`.
EventHandler = Callable[["Event"], None]

#: Wildcard topic: handlers subscribed to this receive every published event.
WILDCARD: str = "*"


@dataclass(frozen=True, slots=True)
class Event:
    """An immutable fact that something happened.

    ``name`` is a dotted topic (e.g. ``"member.created"``). ``payload`` carries DTO-safe data
    only — never ORM entities or secrets.
    """

    name: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)


class EventBus:
    """Thread-safe synchronous event dispatcher."""

    def __init__(
        self, on_handler_error: Callable[[Event, BaseException], None] | None = None
    ) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = threading.RLock()
        self._on_handler_error = on_handler_error

    def set_error_sink(self, sink: Callable[[Event, BaseException], None]) -> None:
        """Inject the error handler (called by the composition root once logging exists)."""
        with self._lock:
            self._on_handler_error = sink

    def subscribe(self, topic: str, handler: EventHandler) -> Callable[[], None]:
        """Register ``handler`` for ``topic`` (or :data:`WILDCARD`). Returns an unsubscribe fn."""
        with self._lock:
            self._handlers[topic].append(handler)

        def _unsubscribe() -> None:
            self.unsubscribe(topic, handler)

        return _unsubscribe

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        with self._lock:
            handlers = self._handlers.get(topic)
            if handlers and handler in handlers:
                handlers.remove(handler)
                if not handlers:
                    del self._handlers[topic]

    def publish(self, event: Event) -> None:
        """Synchronously deliver ``event`` to topic subscribers and wildcard subscribers."""
        with self._lock:
            targets = list(self._handlers.get(event.name, ()))
            targets.extend(self._handlers.get(WILDCARD, ()))

        for handler in targets:
            try:
                handler(event)
            except BaseException as exc:  # noqa: BLE001 - isolation boundary: one bad listener
                if self._on_handler_error is not None:
                    # Never let the error sink itself break dispatch.
                    with contextlib.suppress(BaseException):
                        self._on_handler_error(event, exc)

    def clear(self) -> None:
        """Remove all subscriptions (used by tests and at shutdown)."""
        with self._lock:
            self._handlers.clear()
