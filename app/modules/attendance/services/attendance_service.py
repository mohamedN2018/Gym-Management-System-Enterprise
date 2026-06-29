"""Attendance service — check-in decisioning and history.

A check-in finds the member by membership number, verifies an active subscription (via the
membership service — modules talk through services, Part 2), records the attempt (allowed or
rejected) for audit, and returns a :class:`CheckInResult` for the UI.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from app.core.base.service import BaseService
from app.core.events import Event, EventBus
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.attendance.dtos import AttendanceDTO, CheckInResult
from app.modules.attendance.events import AttendanceEvents
from app.modules.attendance.models.attendance import Attendance
from app.modules.attendance.repositories import AttendanceRepository
from app.modules.members.repositories import MemberRepository
from app.modules.membership.services import MembershipService

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]
NowProvider = Callable[[], datetime]


class AttendanceService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        membership_service: MembershipService,
        now_provider: NowProvider,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._membership = membership_service
        self._now = now_provider
        self._logging = logging

    def check_in(self, membership_number: str) -> Result[CheckInResult]:
        return self._guard(lambda: self._check_in(membership_number), message="Check-in failed")

    def _check_in(self, membership_number: str) -> CheckInResult:
        number = (membership_number or "").strip()
        with self._uow_factory() as uow:
            member = MemberRepository(uow.session).find_by_membership_number(number)
            if member is None:
                self._publish(
                    Event(AttendanceEvents.REJECTED, {"number": number, "reason": "not_found"})
                )
                return CheckInResult(allowed=False, reason="not_found", membership_number=number)
            member_id, member_name = member.id, member.full_name

        active = self._membership.active_subscription(member_id)
        active_dto = active.value if active.is_success else None
        allowed = active_dto is not None
        reason = "ok" if allowed else "no_active_subscription"

        with self._uow_factory() as uow:
            AttendanceRepository(uow.session).add(
                Attendance(
                    member_id=member_id,
                    membership_number=number,
                    checked_in_at=self._now(),
                    allowed=allowed,
                    reason=reason,
                )
            )
            uow.commit()

        if self._logging:
            self._logging.audit(
                action="check_in",
                module="attendance",
                result="success" if allowed else "rejected",
                new_value={"member_id": member_id, "number": number, "reason": reason},
            )
        self._publish(
            Event(
                AttendanceEvents.CHECKED_IN if allowed else AttendanceEvents.REJECTED,
                {"member_id": member_id, "number": number},
            )
        )
        return CheckInResult(
            allowed=allowed,
            reason=reason,
            membership_number=number,
            member_name=member_name,
            plan_name=active_dto.plan_name if active_dto else None,
            remaining_days=active_dto.remaining_days if active_dto else None,
        )

    def today_count(self) -> int:
        start, end = self._today_bounds()
        with self._uow_factory() as uow:
            return AttendanceRepository(uow.session).count_between(start, end, allowed_only=True)

    def list_today(self) -> Result[list[AttendanceDTO]]:
        def _list() -> list[AttendanceDTO]:
            start, end = self._today_bounds()
            with self._uow_factory() as uow:
                members = MemberRepository(uow.session)
                rows = AttendanceRepository(uow.session).list_between(start, end)
                result: list[AttendanceDTO] = []
                for row in rows:
                    member = members.get(row.member_id, include_deleted=True)
                    result.append(
                        AttendanceDTO(
                            id=row.id,
                            membership_number=row.membership_number,
                            member_name=member.full_name if member else row.membership_number,
                            checked_in_at=row.checked_in_at,
                            allowed=row.allowed,
                            reason=row.reason,
                        )
                    )
                return result

        return self._guard(_list, message="Could not list attendance")

    def _today_bounds(self) -> tuple[datetime, datetime]:
        now = self._now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
