"""Input validators for the security module."""

from __future__ import annotations

from app.core.base.validator import (
    BaseValidator,
    ValidationResult,
    is_email,
    max_length,
    min_length,
    required,
)
from app.modules.security.dtos import CreateUserRequest, LoginRequest


class LoginValidator(BaseValidator[LoginRequest]):
    def validate(self, data: LoginRequest) -> ValidationResult:
        result = ValidationResult()
        if msg := required(data.username, "username"):
            result.add("username", msg)
        if msg := required(data.password, "password"):
            result.add("password", msg)
        return result


class CreateUserValidator(BaseValidator[CreateUserRequest]):
    USERNAME_MIN = 3
    USERNAME_MAX = 80
    PASSWORD_MIN = 8

    def validate(self, data: CreateUserRequest) -> ValidationResult:
        result = ValidationResult()
        if msg := required(data.username, "username"):
            result.add("username", msg)
        else:
            if msg := min_length(data.username, self.USERNAME_MIN, "username"):
                result.add("username", msg)
            if msg := max_length(data.username, self.USERNAME_MAX, "username"):
                result.add("username", msg)

        if (msg := required(data.password, "password")) or (
            msg := min_length(data.password, self.PASSWORD_MIN, "password")
        ):
            result.add("password", msg)

        if data.email and (msg := is_email(data.email, "email")):
            result.add("email", msg)
        return result
