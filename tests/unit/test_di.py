import pytest
from app.core.di import Container
from app.core.errors import ConfigurationError

pytestmark = pytest.mark.unit


class _A:
    pass


def test_register_and_resolve_instance():
    container = Container()
    instance = _A()
    container.register_instance(_A, instance)
    assert container.resolve(_A) is instance
    assert container.has(_A)


def test_singleton_factory_invoked_once():
    container = Container()
    calls: list[int] = []
    container.register_factory(_A, lambda _c: (calls.append(1), _A())[1])
    first = container.resolve(_A)
    second = container.resolve(_A)
    assert first is second
    assert len(calls) == 1


def test_transient_factory_new_each_time():
    container = Container()
    container.register_factory(_A, lambda _c: _A(), singleton=False)
    assert container.resolve(_A) is not container.resolve(_A)


def test_missing_registration_raises():
    with pytest.raises(ConfigurationError):
        Container().resolve(_A)


def test_string_key_and_dependency_resolution():
    container = Container()
    container.register_instance("n", 5)
    container.register_factory("double", lambda c: c.resolve("n") * 2)
    assert container.resolve("double") == 10
