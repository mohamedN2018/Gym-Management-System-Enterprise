import pytest
from app.modules.membership.dtos import CreatePlanRequest
from app.modules.membership.validators import CreatePlanValidator

pytestmark = pytest.mark.unit


def test_accepts_valid_plan():
    request = CreatePlanRequest(name="Monthly", price=300, duration_days=30)
    assert CreatePlanValidator().validate(request).is_valid


def test_requires_name():
    result = CreatePlanValidator().validate(CreatePlanRequest(name="", price=10, duration_days=30))
    assert "name" in result.errors


def test_flags_negative_price_and_zero_duration():
    result = CreatePlanValidator().validate(
        CreatePlanRequest(name="Bad", price=-1, duration_days=0)
    )
    assert "price" in result.errors
    assert "duration_days" in result.errors
