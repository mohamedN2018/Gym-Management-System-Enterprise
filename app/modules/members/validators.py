"""Member input validators."""

from __future__ import annotations

from app.core.base.validator import (
    BaseValidator,
    ValidationResult,
    is_email,
    is_phone,
    max_length,
    required,
)
from app.modules.members.dtos import CreateMemberRequest


class CreateMemberValidator(BaseValidator[CreateMemberRequest]):
    NAME_MAX = 100

    def validate(self, data: CreateMemberRequest) -> ValidationResult:
        result = ValidationResult()
        if (msg := required(data.first_name, "first_name")) or (
            msg := max_length(data.first_name, self.NAME_MAX, "first_name")
        ):
            result.add("first_name", msg)

        if msg := max_length(data.last_name, self.NAME_MAX, "last_name"):
            result.add("last_name", msg)
        if data.phone and (msg := is_phone(data.phone, "phone")):
            result.add("phone", msg)
        if data.email and (msg := is_email(data.email, "email")):
            result.add("email", msg)
        return result
