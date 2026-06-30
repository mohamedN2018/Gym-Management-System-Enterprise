"""MemberMeasurement entity — a member's body metrics at a point in time."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Entity


class MemberMeasurement(Entity):
    __tablename__ = "member_measurements"

    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True, nullable=False
    )
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    @property
    def bmi(self) -> Decimal | None:
        """Body mass index (kg / m²), derived — never stored (3NF)."""
        if not self.weight_kg or not self.height_cm or self.height_cm == 0:
            return None
        height_m = self.height_cm / Decimal("100")
        return (self.weight_kg / (height_m * height_m)).quantize(Decimal("0.01"))
