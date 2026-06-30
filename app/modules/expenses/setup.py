"""Expenses module wiring."""

from __future__ import annotations

from datetime import datetime

from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY
from app.logs.logging_service import LoggingService
from app.modules.expenses.services import ExpenseService


def register_expense_services(container) -> None:
    container.register_factory(
        ExpenseService,
        lambda c: ExpenseService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            now_provider=datetime.now,
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
