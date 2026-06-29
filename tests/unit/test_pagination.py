import pytest
from app.core.constants import MAX_PAGE_SIZE
from app.core.pagination import Page, PageRequest, Sort, SortDirection

pytestmark = pytest.mark.unit


def test_request_clamps_bounds():
    big = PageRequest(page=0, size=99_999)
    assert big.page == 1
    assert big.size == MAX_PAGE_SIZE
    small = PageRequest(page=-5, size=0)
    assert small.page == 1
    assert small.size == 1


def test_offset_and_limit():
    req = PageRequest(page=3, size=20)
    assert req.offset == 40
    assert req.limit == 20


def test_search_is_stripped_and_nulled():
    assert PageRequest(search="   ").search is None
    assert PageRequest(search="  hi ").search == "hi"


def test_page_navigation_flags():
    first = Page(items=[1, 2], total=5, page=1, size=2)
    assert first.total_pages == 3
    assert first.has_next is True
    assert first.has_previous is False

    last = Page(items=[5], total=5, page=3, size=2)
    assert last.has_previous is True
    assert last.has_next is False


def test_sort_helpers():
    assert Sort.desc("x").direction is SortDirection.DESC
    assert Sort.asc("x").direction is SortDirection.ASC
    assert SortDirection.DESC.is_descending is True


def test_empty_page():
    page = Page.empty(PageRequest(page=2, size=10))
    assert page.items == []
    assert page.total == 0
    assert page.page == 2
