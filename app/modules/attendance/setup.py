"""Attendance module wiring."""

from __future__ import annotations

from datetime import datetime

from app.core.di import Container
from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY
from app.logs.logging_service import LoggingService
from app.modules.attendance.services import AttendanceService
from app.modules.membership.services import MembershipService


def register_attendance_services(container: Container) -> None:
    container.register_factory(
        AttendanceService,
        lambda c: AttendanceService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            membership_service=c.resolve(MembershipService),
            now_provider=datetime.now,
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
