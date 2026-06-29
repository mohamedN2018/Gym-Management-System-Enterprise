import pytest
from app.core.errors import ErrorCode, NotFoundError
from app.core.result import Result

pytestmark = pytest.mark.unit


def test_ok_carries_value():
    r = Result.ok(5)
    assert r.is_success and not r.is_failure
    assert r.value == 5
    assert bool(r) is True
    assert r.unwrap_or(0) == 5
    assert r.error is None


def test_fail_from_string():
    r = Result.fail("boom", ErrorCode.VALIDATION)
    assert r.is_failure and not r.is_success
    assert r.error.code == ErrorCode.VALIDATION
    assert r.error.message == "boom"
    assert r.unwrap_or(42) == 42
    assert bool(r) is False


def test_value_raises_on_failure():
    with pytest.raises(ValueError):
        _ = Result.fail("nope").value


def test_fail_from_app_error_preserves_code_and_details():
    r = Result.fail(NotFoundError("missing", details={"id": 1}))
    assert r.error.code == ErrorCode.NOT_FOUND
    assert r.error.details == {"id": 1}


def test_map_transforms_success_and_passes_failure():
    assert Result.ok(2).map(lambda x: x + 1).value == 3
    assert Result.fail("e").map(lambda x: x + 1).is_failure


def test_and_then_chains_and_short_circuits():
    assert Result.ok(2).and_then(lambda x: Result.ok(x * 10)).value == 20
    assert Result.fail("e").and_then(lambda x: Result.ok(x)).is_failure
