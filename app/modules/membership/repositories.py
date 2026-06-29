"""Membership repositories (persistence only)."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.membership.models.plan import MembershipPlan
from app.modules.membership.models.subscription import Subscription, SubscriptionStatus


class PlanRepository(SqlAlchemyRepository[MembershipPlan]):
    searchable_fields = ("code", "name")

    def __init__(self, session: Session) -> None:
        super().__init__(MembershipPlan, session)

    def find_by_code(self, code: str) -> MembershipPlan | None:
        return self.find_one(code=code)


class SubscriptionRepository(SqlAlchemyRepository[Subscription]):
    def __init__(self, session: Session) -> None:
        super().__init__(Subscription, session)

    def active_for_member(self, member_id: int, on: date) -> Subscription | None:
        """Return the member's currently-valid subscription, if any."""
        stmt = (
            select(Subscription)
            .where(
                Subscription.is_deleted.is_(False),
                Subscription.member_id == member_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.start_date <= on,
                Subscription.end_date >= on,
            )
            .order_by(Subscription.end_date.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalars().first()

    def expiring_within(self, today: date, days: int) -> list[Subscription]:
        """Active subscriptions whose end date falls within ``[today, today+days]``."""
        horizon = today + timedelta(days=days)
        stmt = (
            select(Subscription)
            .where(
                Subscription.is_deleted.is_(False),
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date >= today,
                Subscription.end_date <= horizon,
            )
            .order_by(Subscription.end_date.asc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def count_active(self, on: date) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(Subscription)
            .where(
                Subscription.is_deleted.is_(False),
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.start_date <= on,
                Subscription.end_date >= on,
            )
        )
        return int(self._session.execute(stmt).scalar_one())
