import pytest
from app.modules.security.dtos import CreateUserRequest, LoginRequest
from app.modules.security.validators import CreateUserValidator, LoginValidator

pytestmark = pytest.mark.unit


def test_login_validator_accepts_filled_credentials():
    assert LoginValidator().validate(LoginRequest(username="a", password="b")).is_valid


def test_login_validator_flags_missing_fields():
    result = LoginValidator().validate(LoginRequest(username="", password=""))
    assert not result.is_valid
    assert "username" in result.errors
    assert "password" in result.errors


def test_create_user_validator_accepts_valid_input():
    request = CreateUserRequest(username="alice", password="Passw0rd!", email="a@b.com")
    assert CreateUserValidator().validate(request).is_valid


def test_create_user_validator_flags_short_values():
    result = CreateUserValidator().validate(CreateUserRequest(username="ab", password="short"))
    assert "username" in result.errors
    assert "password" in result.errors


def test_create_user_validator_flags_bad_email():
    request = CreateUserRequest(username="alice", password="Passw0rd!", email="not-an-email")
    result = CreateUserValidator().validate(request)
    assert "email" in result.errors
