"""Centralized logging (Part 1/2: *use LoggingService; never print*).

Exposes :class:`~app.logs.logging_service.LoggingService`, which configures a human-readable
diagnostic log and a separate machine-readable, append-only **audit** trail.
"""

from app.logs.logging_service import LoggingService

__all__ = ["LoggingService"]
