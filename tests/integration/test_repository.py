import pytest
from app.core.errors import ConcurrencyError, ConflictError, DatabaseError, NotFoundError
from app.core.pagination import PageRequest, Sort

from tests.support.sample_models import Widget, WidgetRepository

pytestmark = pytest.mark.integration


def _add(repo: WidgetRepository, name: str, sku: str, by: int = 1) -> Widget:
    return repo.add(Widget(name=name, sku=sku, created_by=by))


def test_add_then_get(make_uow):
    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        widget = _add(repo, "Alpha", "S1")
        uow.commit()
        wid, wuuid = widget.id, widget.uuid

    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        got = repo.get(wid)
        assert got is not None
        assert got.name == "Alpha"
        assert got.version == 1
        assert got.is_deleted is False
        assert got.is_active is True
        assert got.created_at is not None
        assert repo.get_by_uuid(wuuid).id == wid


def test_get_or_raise_raises_not_found(make_uow):
    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        with pytest.raises(NotFoundError):
            repo.get_or_raise(999)


def test_unique_constraint_raises_conflict(make_uow):
    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        _add(repo, "A", "DUP")
        with pytest.raises(ConflictError):
            _add(repo, "B", "DUP")


def test_pagination_and_sorting(make_uow):
    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        for i in range(5):
            _add(repo, f"W{i}", f"S{i}")
        uow.commit()

        page = repo.list(PageRequest(page=1, size=2, sort=(Sort.desc("name"),)))
        assert page.total == 5
        assert len(page.items) == 2
        assert page.items[0].name == "W4"
        assert page.total_pages == 3
        assert page.has_next is True


def test_search(make_uow):
    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        _add(repo, "Treadmill", "T1")
        _add(repo, "Dumbbell", "D1")
        uow.commit()

        result = repo.list(PageRequest(search="tread"))
        assert result.total == 1
        assert result.items[0].name == "Treadmill"


def test_soft_delete_and_restore(make_uow):
    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        widget = _add(repo, "X", "X1")
        uow.commit()
        wid = widget.id

    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        widget = repo.get(wid)
        repo.soft_delete(widget, by=2)
        uow.commit()
        assert widget.is_deleted is True
        assert widget.deleted_by == 2
        assert widget.version == 2

    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        assert repo.get(wid) is None  # excluded by default
        assert repo.count() == 0
        assert repo.count(include_deleted=True) == 1
        widget = repo.get(wid, include_deleted=True)
        repo.restore(widget, by=3)
        uow.commit()
        assert widget.is_deleted is False
        assert widget.is_active is True

    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        assert repo.get(wid) is not None


def test_unknown_filter_field_raises(make_uow):
    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        with pytest.raises(DatabaseError):
            repo.find(nonexistent="x")


def test_optimistic_concurrency_conflict(make_uow):
    with make_uow() as uow:
        repo = WidgetRepository(uow.session)
        widget = _add(repo, "C", "C1")
        uow.commit()
        wid = widget.id

    u1, u2 = make_uow(), make_uow()
    with u1, u2:
        r1, r2 = WidgetRepository(u1.session), WidgetRepository(u2.session)
        w1, w2 = r1.get(wid), r2.get(wid)

        w1.name = "One"
        r1.update(w1)
        u1.commit()  # bumps version 1 -> 2 in the database

        w2.name = "Two"
        with pytest.raises(ConcurrencyError):
            r2.update(w2)  # still believes version == 1
