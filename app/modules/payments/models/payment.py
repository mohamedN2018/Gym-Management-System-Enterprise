"""Payment entity — a single money-received record."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Entity


class PaymentMethod:
    CASH = "cash"
    CARD = "card"
    WALLET = "wallet"
    TRANSFER = "transfer"


class PaymentType:
    SUBSCRIPTION = "subscription"
    POS = "pos"
    OTHER = "other"


class Payment(Entity):
    __tablename__ = "payments"

    #: Optional — POS/other payments may not be tied to a member.
    member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id", ondelete="SET NULL"), index=True, nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False, default=PaymentMethod.CASH)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False, default=PaymentType.OTHER)
    reference: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
