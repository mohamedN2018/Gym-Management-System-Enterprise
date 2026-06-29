"""Pagination, sorting and search request/response value objects.

Repositories accept a :class:`PageRequest` and return a :class:`Page`. This keeps large
dataset access lazy and bounded (Part 2: *use pagination, lazy load large datasets*).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Generic, TypeVar

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_NUMBER

T = TypeVar("T")


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"

    @property
    def is_descending(self) -> bool:
        return self is SortDirection.DESC


@dataclass(frozen=True, slots=True)
class Sort:
    """A single sort instruction. ``field`` is a model attribute name (validated by the repo)."""

    field: str
    direction: SortDirection = SortDirection.ASC

    @classmethod
    def asc(cls, field: str) -> Sort:
        return cls(field, SortDirection.ASC)

    @classmethod
    def desc(cls, field: str) -> Sort:
        return cls(field, SortDirection.DESC)


@dataclass(frozen=True, slots=True)
class PageRequest:
    """A bounded request for a slice of a dataset.

    ``page`` is 1-based. ``size`` is clamped to ``[1, MAX_PAGE_SIZE]`` and ``page`` to ``>= 1``
    so that a hostile or buggy caller can never request an unbounded result set.
    """

    page: int = MIN_PAGE_NUMBER
    size: int = DEFAULT_PAGE_SIZE
    sort: tuple[Sort, ...] = ()
    search: str | None = None
    filters: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "page", max(MIN_PAGE_NUMBER, int(self.page)))
        object.__setattr__(self, "size", max(1, min(int(self.size), MAX_PAGE_SIZE)))
        search = self.search.strip() if isinstance(self.search, str) else None
        object.__setattr__(self, "search", search or None)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """A materialized page of results plus the total count for the underlying query."""

    items: list[T]
    total: int
    page: int
    size: int

    @property
    def total_pages(self) -> int:
        if self.size <= 0:
            return 0
        return (self.total + self.size - 1) // self.size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > MIN_PAGE_NUMBER

    @classmethod
    def empty(cls, request: PageRequest) -> Page[T]:
        return cls(items=[], total=0, page=request.page, size=request.size)
