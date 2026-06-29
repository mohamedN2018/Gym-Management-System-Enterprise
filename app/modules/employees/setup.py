"""Employees module wiring."""

from __future__ import annotations

from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY
from app.logs.logging_service import LoggingService
from app.modules.employees.services import EmployeeService


def register_employee_services(container) -> None:
    container.register_factory(
        EmployeeService,
        lambda c: EmployeeService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
