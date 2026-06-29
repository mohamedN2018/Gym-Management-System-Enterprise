"""Attendance DTOs."""

from __future__ import annotations

from datetime import datetime

from app.core.base.dto import BaseDTO


class CheckInResult(BaseDTO):
    """Outcome of a check-in attempt (drives the success/reject screen)."""

    allowed: bool
    reason: str  # "ok" | "not_found" | "no_active_subscription"
    membership_number: str
    member_name: str | None = None
    plan_name: str | None = None
    remaining_days: int | None = None


class AttendanceDTO(BaseDTO):
    id: int
    membership_number: str
    member_name: str
    checked_in_at: datetime
    allowed: bool
    reason: str
