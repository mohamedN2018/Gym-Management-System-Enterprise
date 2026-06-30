"""Expenses module event topics."""

from __future__ import annotations


class ExpenseEvents:
    RECORDED = "expenses.expense.recorded"
    UPDATED = "expenses.expense.updated"
    DELETED = "expenses.expense.deleted"
