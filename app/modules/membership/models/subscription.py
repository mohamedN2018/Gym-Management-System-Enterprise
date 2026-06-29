"""Subscription entity — links a member to a plan for a date range."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Entity
from app.modules.membership.models.plan import MembershipPlan


class SubscriptionStatus:
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FROZEN = "frozen"


class Subscription(Entity):
    __tablename__ = "subscriptions"

    # FK by table name keeps this module decoupled from the members ORM class.
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("membership_plans.id"), index=True, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    price_paid: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        server_default=text("'active'"),
    )

    plan: Mapped[MembershipPlan] = relationship(lazy="joined")

    def is_active_on(self, on: date) -> bool:
        return self.status == SubscriptionStatus.ACTIVE and self.start_date <= on <= self.end_date
