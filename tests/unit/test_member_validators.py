import pytest
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.validators import CreateMemberValidator

pytestmark = pytest.mark.unit


def test_accepts_minimal_valid_member():
    assert CreateMemberValidator().validate(CreateMemberRequest(first_name="Ali")).is_valid


def test_requires_first_name():
    result = CreateMemberValidator().validate(CreateMemberRequest(first_name=""))
    assert "first_name" in result.errors


def test_flags_invalid_phone_and_email():
    request = CreateMemberRequest(first_name="Ali", phone="abc", email="bad")
    result = CreateMemberValidator().validate(request)
    assert "phone" in result.errors
    assert "email" in result.errors


def test_accepts_valid_contact_details():
    request = CreateMemberRequest(first_name="Ali", phone="+201234567", email="a@b.com")
    assert CreateMemberValidator().validate(request).is_valid
