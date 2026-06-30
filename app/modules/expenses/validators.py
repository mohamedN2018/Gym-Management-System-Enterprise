"""Expense input validators."""

from __future__ import annotations

from app.core.base.validator import BaseValidator, ValidationResult, in_range, required
from app.modules.expenses.dtos import RecordExpenseRequest


class RecordExpenseValidator(BaseValidator[RecordExpenseRequest]):
    def validate(self, data: RecordExpenseRequest) -> ValidationResult:
        result = ValidationResult()
        if msg := required(data.category, "category"):
            result.add("category", msg)
        if msg := in_range(float(data.amount), 0, None, "amount"):
            result.add("amount", msg)
        return result
