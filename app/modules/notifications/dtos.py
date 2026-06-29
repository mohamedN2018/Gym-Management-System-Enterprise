"""Notification DTOs."""

from __future__ import annotations

from pydantic import Field

from app.core.base.dto import BaseDTO


class AlertSeverity:
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


class AlertDTO(BaseDTO):
    """A single actionable alert. ``key``/``params`` are localized by the UI."""

    category: str
    severity: str
    key: str
    params: dict[str, str] = Field(default_factory=dict)
