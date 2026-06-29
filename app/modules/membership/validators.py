"""Membership input validators."""

from __future__ import annotations

from app.core.base.validator import BaseValidator, ValidationResult, in_range, max_length, required
from app.modules.membership.dtos import CreatePlanRequest


class CreatePlanValidator(BaseValidator[CreatePlanRequest]):
    NAME_MAX = 120

    def validate(self, data: CreatePlanRequest) -> ValidationResult:
        result = ValidationResult()
        if (msg := required(data.name, "name")) or (
            msg := max_length(data.name, self.NAME_MAX, "name")
        ):
            result.add("name", msg)
        if msg := in_range(float(data.price), 0, None, "price"):
            result.add("price", msg)
        if msg := in_range(data.duration_days, 1, None, "duration_days"):
            result.add("duration_days", msg)
        return result
