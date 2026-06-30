"""Expense DTOs + mapper."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.core.base.dto import BaseDTO
from app.modules.expenses.models.expense import Expense


class RecordExpenseRequest(BaseDTO):
    category: str
    amount: Decimal
    note: str | None = None


class ExpenseDTO(BaseDTO):
    id: int
    category: str
    amount: Decimal
    paid_at: datetime
    note: str | None = None


def to_expense_dto(expense: Expense) -> ExpenseDTO:
    return ExpenseDTO(
        id=expense.id,
        category=expense.category,
        amount=expense.amount,
        paid_at=expense.paid_at,
        note=expense.note,
    )
