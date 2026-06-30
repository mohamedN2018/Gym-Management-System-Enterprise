"""Expense repository (persistence only)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.expenses.models.expense import Expense


class ExpenseRepository(SqlAlchemyRepository[Expense]):
    searchable_fields = ("category", "note")

    def __init__(self, session: Session) -> None:
        super().__init__(Expense, session)

    def total(self, start: datetime | None = None, end: datetime | None = None) -> Decimal:
        conditions = [Expense.is_deleted.is_(False)]
        if start is not None:
            conditions.append(Expense.paid_at >= start)
        if end is not None:
            conditions.append(Expense.paid_at < end)
        stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(*conditions)
        return Decimal(str(self._session.execute(stmt).scalar_one()))
