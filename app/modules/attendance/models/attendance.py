"""Attendance entity — one member check-in event."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Entity


class Attendance(Entity):
    __tablename__ = "attendance"

    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: Snapshot of the scanned/entered number (kept even if the member is later renumbered).
    membership_number: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    #: Whether entry was granted.
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    #: Machine reason code (``ok`` / ``no_active_subscription`` / …).
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
