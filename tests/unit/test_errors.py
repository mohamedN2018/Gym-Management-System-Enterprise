import pytest
from app.core.errors import (
    AppError,
    DatabaseError,
    ErrorCode,
    NotFoundError,
    ValidationError,
)

pytestmark = pytest.mark.unit


def test_base_defaults():
    e = AppError("x")
    assert e.code is ErrorCode.UNKNOWN
    assert e.is_operational is True
    assert e.to_dict() == {
        "code": "UNKNOWN",
        "message": "x",
        "details": {},
        "is_operational": True,
    }


def test_subclass_codes():
    assert ValidationError("v").code is ErrorCode.VALIDATION
    assert NotFoundError("n").code is ErrorCode.NOT_FOUND


def test_infrastructure_errors_are_non_operational():
    assert DatabaseError("d").is_operational is False


def test_overrides():
    e = ValidationError("v", code=ErrorCode.CONFLICT, is_operational=False, details={"f": 1})
    assert e.code is ErrorCode.CONFLICT
    assert e.is_operational is False
    assert e.details == {"f": 1}


def test_str_and_cause():
    cause = ValueError("root")
    e = NotFoundError("missing", cause=cause)
    assert str(e) == "[NOT_FOUND] missing"
    assert e.__cause__ is cause
