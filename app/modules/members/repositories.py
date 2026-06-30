"""Member repository (persistence only)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.members.models.measurement import MemberMeasurement
from app.modules.members.models.member import Member


class MemberRepository(SqlAlchemyRepository[Member]):
    searchable_fields = (
        "membership_number",
        "first_name",
        "last_name",
        "phone",
        "email",
        "national_id",
    )

    def __init__(self, session: Session) -> None:
        super().__init__(Member, session)

    def find_by_membership_number(self, membership_number: str) -> Member | None:
        return self.find_one(membership_number=membership_number)


class MeasurementRepository(SqlAlchemyRepository[MemberMeasurement]):
    def __init__(self, session: Session) -> None:
        super().__init__(MemberMeasurement, session)

    def for_member(self, member_id: int) -> list[MemberMeasurement]:
        """All of a member's measurements, newest first."""
        stmt = (
            select(MemberMeasurement)
            .where(
                MemberMeasurement.is_deleted.is_(False),
                MemberMeasurement.member_id == member_id,
            )
            .order_by(MemberMeasurement.measured_at.desc())
        )
        return list(self._session.execute(stmt).scalars().all())
