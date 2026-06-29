import pytest
from app.core.errors import InfrastructureError, ValidationError
from app.security.encryption import EncryptionService
from app.security.password_hasher import PasswordHasher

pytestmark = pytest.mark.unit


def test_hash_and_verify():
    hasher = PasswordHasher()
    hashed = hasher.hash("secret123")
    assert hashed != "secret123"
    assert hasher.verify(hashed, "secret123") is True
    assert hasher.verify(hashed, "wrong") is False


def test_hash_rejects_empty():
    with pytest.raises(ValidationError):
        PasswordHasher().hash("")


def test_verify_fails_closed_on_garbage():
    hasher = PasswordHasher()
    assert hasher.verify("not-a-hash", "x") is False
    assert hasher.verify("", "x") is False


def test_needs_rehash():
    hasher = PasswordHasher()
    assert hasher.needs_rehash("garbage") is True
    assert hasher.needs_rehash(hasher.hash("ok")) is False


def test_encryption_roundtrip(tmp_path):
    service = EncryptionService.from_key_file(tmp_path / "k.key")
    token = service.encrypt("hello")
    assert token != "hello"
    assert service.decrypt(token) == "hello"


def test_encryption_key_is_persisted_and_reused(tmp_path):
    key_path = tmp_path / "k.key"
    token = EncryptionService.from_key_file(key_path).encrypt("x")
    assert key_path.exists()
    # A new service loading the same key file can still decrypt.
    assert EncryptionService.from_key_file(key_path).decrypt(token) == "x"


def test_decrypt_rejects_tampered_token(tmp_path):
    service = EncryptionService.from_key_file(tmp_path / "k.key")
    with pytest.raises(InfrastructureError):
        service.decrypt("garbage-token")
