import pytest
from app.core.errors import InfrastructureError

from tests.support.sample_models import Widget, WidgetRepository

pytestmark = pytest.mark.integration


def test_commit_persists(make_uow):
    with make_uow() as uow:
        WidgetRepository(uow.session).add(Widget(name="A", sku="S1"))
        uow.commit()
    with make_uow() as uow:
        assert WidgetRepository(uow.session).count() == 1


def test_clean_exit_without_commit_rolls_back(make_uow):
    with make_uow() as uow:
        WidgetRepository(uow.session).add(Widget(name="A", sku="S1"))
        # No commit: per the contract, the unit of work must roll back on exit.
    with make_uow() as uow:
        assert WidgetRepository(uow.session).count() == 0


def test_exception_rolls_back(make_uow):
    with pytest.raises(RuntimeError), make_uow() as uow:
        WidgetRepository(uow.session).add(Widget(name="A", sku="S1"))
        raise RuntimeError("boom")
    with make_uow() as uow:
        assert WidgetRepository(uow.session).count() == 0


def test_session_outside_context_raises(make_uow):
    uow = make_uow()
    with pytest.raises(InfrastructureError):
        _ = uow.session
