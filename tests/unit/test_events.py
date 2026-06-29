import pytest
from app.core.events import WILDCARD, Event, EventBus

pytestmark = pytest.mark.unit


def test_publish_only_to_matching_topic():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("a", lambda e: seen.append(e.name))
    bus.publish(Event("a"))
    bus.publish(Event("b"))
    assert seen == ["a"]


def test_wildcard_receives_all():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe(WILDCARD, lambda e: seen.append(e.name))
    bus.publish(Event("x"))
    bus.publish(Event("y"))
    assert seen == ["x", "y"]


def test_unsubscribe():
    bus = EventBus()
    seen: list[int] = []
    off = bus.subscribe("a", lambda e: seen.append(1))
    off()
    bus.publish(Event("a"))
    assert seen == []


def test_payload_access():
    bus = EventBus()
    got: dict[str, object] = {}
    bus.subscribe("a", lambda e: got.update(id=e.get("id")))
    bus.publish(Event("a", {"id": 7}))
    assert got["id"] == 7


def test_handler_error_is_routed_not_raised():
    errors: list[tuple[str, str]] = []
    bus = EventBus(on_handler_error=lambda e, exc: errors.append((e.name, type(exc).__name__)))
    good_seen: list[int] = []

    def bad(_e: Event) -> None:
        raise RuntimeError("boom")

    bus.subscribe("a", bad)
    bus.subscribe("a", lambda e: good_seen.append(1))

    bus.publish(Event("a"))  # must not raise

    assert errors == [("a", "RuntimeError")]
    assert good_seen == [1]  # a failing listener does not stop the others
