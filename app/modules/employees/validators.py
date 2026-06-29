"""Employee input validators."""

from __future__ import annotations

from app.core.base.validator import BaseValidator, ValidationResult, is_phone, max_length, required
from app.modules.employees.dtos import CreateEmployeeRequest


class CreateEmployeeValidator(BaseValidator[CreateEmployeeRequest]):
    NAME_MAX = 100

    def validate(self, data: CreateEmployeeRequest) -> ValidationResult:
        result = ValidationResult()
        if (msg := required(data.first_name, "first_name")) or (
            msg := max_length(data.first_name, self.NAME_MAX, "first_name")
        ):
            result.add("first_name", msg)
        if data.phone and (msg := is_phone(data.phone, "phone")):
            result.add("phone", msg)
        return result
