import pytest
from app.core.base.validator import (
    BaseValidator,
    ValidationResult,
    in_range,
    is_email,
    is_phone,
    max_length,
    min_length,
    required,
)
from app.core.errors import ValidationError

pytestmark = pytest.mark.unit


def test_required():
    assert required("", "name")
    assert required(None)
    assert required("ok") is None


def test_email():
    assert is_email("bad")
    assert is_email("a@b.com") is None
    assert is_email("") is None  # emptiness is checked by `required`, not `is_email`


def test_phone():
    assert is_phone("12")
    assert is_phone("+201234567") is None
    assert is_phone("(020) 123-4567") is None


def test_lengths():
    assert max_length("abcd", 3)
    assert max_length("ab", 3) is None
    assert min_length("a", 2)
    assert min_length("abc", 2) is None


def test_in_range():
    assert in_range(5, 1, 3)
    assert in_range(2, 1, 3) is None
    assert in_range(None, 1, 3) is None


def test_validation_result_accumulates_and_raises():
    result = ValidationResult()
    assert result.is_valid
    result.add("name", "required")
    assert not result.is_valid
    with pytest.raises(ValidationError) as info:
        result.raise_if_invalid()
    assert info.value.details == {"fields": {"name": ["required"]}}


def test_validation_result_merge():
    a = ValidationResult().add("x", "1")
    b = ValidationResult().add("y", "2")
    a.merge(b)
    assert set(a.errors) == {"x", "y"}


def test_base_validator():
    class NameValidator(BaseValidator):
        def validate(self, data):
            result = ValidationResult()
            if msg := required(data.get("name"), "name"):
                result.add("name", msg)
            return result

    NameValidator().validate_and_raise({"name": "ok"})
    with pytest.raises(ValidationError):
        NameValidator().validate_and_raise({"name": ""})
