"""Repository interface (persistence contract).

Repositories perform persistence only — CRUD, filtering, pagination, search, sorting — and
**no business logic** (Part 2). Services depend on this abstraction, not on the SQLAlchemy
implementation in :mod:`app.database.repository`, keeping the domain testable and the ORM
swappable (SQLite -> PostgreSQL).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from app.core.pagination import Page, PageRequest

#: The persisted entity type.
TEntity = TypeVar("TEntity")
#: The primary-key type (``int`` for our autoincrement ids).
TId = TypeVar("TId")


class IRepository(ABC, Generic[TEntity, TId]):
    """Generic CRUD + query contract for a single aggregate/entity type.

    Implementations must, by default, exclude soft-deleted rows from reads unless a method
    explicitly opts in via ``include_deleted``.
    """

    # --- read -------------------------------------------------------------
    @abstractmethod
    def get(self, entity_id: TId, *, include_deleted: bool = False) -> TEntity | None:
        """Return the entity with the given primary key, or ``None`` if not found."""

    @abstractmethod
    def get_or_raise(self, entity_id: TId, *, include_deleted: bool = False) -> TEntity:
        """Return the entity or raise :class:`~app.core.errors.NotFoundError`."""

    @abstractmethod
    def get_by_uuid(self, uuid: str, *, include_deleted: bool = False) -> TEntity | None:
        """Return the entity with the given public UUID, or ``None``."""

    @abstractmethod
    def find(self, *, include_deleted: bool = False, **filters: Any) -> list[TEntity]:
        """Return all entities matching equality ``filters``."""

    @abstractmethod
    def find_one(self, *, include_deleted: bool = False, **filters: Any) -> TEntity | None:
        """Return a single entity matching ``filters`` (the first), or ``None``."""

    @abstractmethod
    def list(self, request: PageRequest, *, include_deleted: bool = False) -> Page[TEntity]:
        """Return a bounded :class:`Page` honoring search/sort/filters in ``request``."""

    @abstractmethod
    def count(self, *, include_deleted: bool = False, **filters: Any) -> int:
        """Return the number of entities matching ``filters``."""

    @abstractmethod
    def exists(self, *, include_deleted: bool = False, **filters: Any) -> bool:
        """Return whether any entity matches ``filters``."""

    # --- write ------------------------------------------------------------
    @abstractmethod
    def add(self, entity: TEntity) -> TEntity:
        """Stage a new entity for insertion. Persisted on unit-of-work commit."""

    @abstractmethod
    def update(self, entity: TEntity) -> TEntity:
        """Stage changes to a tracked entity. Persisted on unit-of-work commit."""

    @abstractmethod
    def soft_delete(self, entity: TEntity, *, by: int | None = None) -> None:
        """Mark the entity deleted (sets ``is_deleted``/``deleted_at``/``deleted_by``)."""

    @abstractmethod
    def restore(self, entity: TEntity, *, by: int | None = None) -> None:
        """Reverse a soft delete, returning the entity to active state."""
