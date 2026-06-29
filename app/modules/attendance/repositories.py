"""Attendance repository (persistence only)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.attendance.models.attendance import Attendance


class AttendanceRepository(SqlAlchemyRepository[Attendance]):
    searchable_fields = ("membership_number",)

    def __init__(self, session: Session) -> None:
        super().__init__(Attendance, session)

    def count_between(self, start: datetime, end: datetime, *, allowed_only: bool = False) -> int:
        conditions = [
            Attendance.is_deleted.is_(False),
            Attendance.checked_in_at >= start,
            Attendance.checked_in_at < end,
        ]
        if allowed_only:
            conditions.append(Attendance.allowed.is_(True))
        stmt = select(func.count()).select_from(Attendance).where(*conditions)
        return int(self._session.execute(stmt).scalar_one())

    def list_between(self, start: datetime, end: datetime) -> list[Attendance]:
        stmt = (
            select(Attendance)
            .where(
                Attendance.is_deleted.is_(False),
                Attendance.checked_in_at >= start,
                Attendance.checked_in_at < end,
            )
            .order_by(Attendance.checked_in_at.desc())
        )
        return list(self._session.execute(stmt).scalars().all())
