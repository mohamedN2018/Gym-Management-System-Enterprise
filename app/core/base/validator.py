"""Validation base + reusable primitive rules.

Every input is validated before a service acts on it (Part 2: *never trust user input*).
A :class:`ValidationResult` accumulates per-field messages so the UI can show all problems at
once, and can be raised as a single :class:`~app.core.errors.ValidationError`.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from app.core.errors import ValidationError

TInput = TypeVar("TInput")

# Pragmatic, locale-tolerant patterns. Stricter domain rules belong in module validators.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# E.164-ish: optional leading +, 7-15 digits, allowing spaces/dashes which are stripped first.
_PHONE_RE = re.compile(r"^\+?\d{7,15}$")


@dataclass(slots=True)
class ValidationResult:
    """Accumulates field-level validation errors."""

    errors: dict[str, list[str]] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add(self, field_name: str, message: str) -> ValidationResult:
        self.errors.setdefault(field_name, []).append(message)
        return self

    def merge(self, other: ValidationResult) -> ValidationResult:
        for field_name, messages in other.errors.items():
            self.errors.setdefault(field_name, []).extend(messages)
        return self

    def raise_if_invalid(self, message: str = "Validation failed") -> None:
        if not self.is_valid:
            raise ValidationError(message, details={"fields": self.errors})


class BaseValidator(ABC, Generic[TInput]):
    """Base for module validators."""

    @abstractmethod
    def validate(self, data: TInput) -> ValidationResult:
        """Return a :class:`ValidationResult` describing all problems with ``data``."""

    def validate_and_raise(self, data: TInput) -> None:
        """Validate and raise :class:`ValidationError` if invalid."""
        self.validate(data).raise_if_invalid()


# --- reusable primitive rules ------------------------------------------------
# Each returns an error message (str) or ``None`` when valid, for use as:
#     if msg := required(value, "name"): result.add("name", msg)


def required(value: object, label: str = "value") -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return f"{label} is required."
    return None


def max_length(value: str | None, limit: int, label: str = "value") -> str | None:
    if value is not None and len(value) > limit:
        return f"{label} must be at most {limit} characters."
    return None


def min_length(value: str | None, limit: int, label: str = "value") -> str | None:
    if value is not None and len(value.strip()) < limit:
        return f"{label} must be at least {limit} characters."
    return None


def is_email(value: str | None, label: str = "email") -> str | None:
    if value and not _EMAIL_RE.match(value):
        return f"{label} is not a valid email address."
    return None


def is_phone(value: str | None, label: str = "phone") -> str | None:
    if value:
        normalized = re.sub(r"[\s\-()]", "", value)
        if not _PHONE_RE.match(normalized):
            return f"{label} is not a valid phone number."
    return None


def in_range(
    value: float | int | None,
    minimum: float | int | None = None,
    maximum: float | int | None = None,
    label: str = "value",
) -> str | None:
    if value is None:
        return None
    if minimum is not None and value < minimum:
        return f"{label} must be at least {minimum}."
    if maximum is not None and value > maximum:
        return f"{label} must be at most {maximum}."
    return None
