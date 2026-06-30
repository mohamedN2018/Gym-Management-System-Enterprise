"""Expense service — record expenses, list them, and report totals."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.base.service import BaseService
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest, Sort
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.expenses.dtos import ExpenseDTO, RecordExpenseRequest, to_expense_dto
from app.modules.expenses.events import ExpenseEvents
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.repositories import ExpenseRepository
from app.modules.expenses.validators import RecordExpenseValidator

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]
NowProvider = Callable[[], datetime]


class ExpenseService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        now_provider: NowProvider,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._now = now_provider
        self._logging = logging
        self._validator = RecordExpenseValidator()

    def record_expense(
        self, request: RecordExpenseRequest, *, created_by: int | None = None
    ) -> Result[ExpenseDTO]:
        def _record() -> ExpenseDTO:
            self._validator.validate_and_raise(request)
            with self._uow_factory() as uow:
                expense = Expense(
                    category=request.category.strip(),
                    amount=request.amount,
                    note=(request.note or None),
                    paid_at=self._now(),
                    created_by=created_by,
                )
                ExpenseRepository(uow.session).add(expense)
                dto = to_expense_dto(expense)
                uow.commit()
            if self._logging:
                self._logging.audit(
                    action="expense",
                    module="expenses",
                    result="success",
                    user=created_by,
                    new_value={"amount": str(dto.amount), "category": dto.category},
                )
            self._publish(Event(ExpenseEvents.RECORDED, {"expense_id": dto.id}))
            return dto

        return self._guard(_record, message="Could not record expense")

    def list_expenses(self, request: PageRequest | None = None) -> Result[Page[ExpenseDTO]]:
        def _list() -> Page[ExpenseDTO]:
            with self._uow_factory() as uow:
                page = ExpenseRepository(uow.session).list(
                    request or PageRequest(sort=(Sort.desc("paid_at"),))
                )
                return Page(
                    items=[to_expense_dto(e) for e in page.items],
                    total=page.total,
                    page=page.page,
                    size=page.size,
                )

        return self._guard(_list, message="Could not list expenses")

    def total_expenses(self) -> Decimal:
        with self._uow_factory() as uow:
            return ExpenseRepository(uow.session).total()

    def today_expenses(self) -> Decimal:
        now = self._now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        with self._uow_factory() as uow:
            return ExpenseRepository(uow.session).total(start, start + timedelta(days=1))
