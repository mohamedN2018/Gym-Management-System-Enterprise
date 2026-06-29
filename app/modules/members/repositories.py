"""Member repository (persistence only)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
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
