"""Reports module wiring."""

from __future__ import annotations

from app.core.di import Container
from app.logs.logging_service import LoggingService
from app.modules.members.services import MemberService
from app.modules.payments.services import PaymentService
from app.modules.reports.services import ReportService


def register_report_services(container: Container) -> None:
    container.register_factory(
        ReportService,
        lambda c: ReportService(
            members=c.resolve(MemberService),
            payments=c.resolve(PaymentService),
            logging=c.resolve(LoggingService),
        ),
    )
