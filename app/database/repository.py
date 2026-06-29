"""Generic SQLAlchemy repository.

Implements :class:`~app.core.base.repository.IRepository` for any :class:`Entity` subclass:
CRUD, equality filtering, full-text-ish search, sorting and pagination — and **no business
logic** (Part 2). Module repositories subclass this to add bespoke queries and to declare
``searchable_fields``.

Soft-deleted rows are excluded from every read unless ``include_deleted=True``.
ORM/DB exceptions are translated into the typed :class:`AppError` hierarchy.
"""

from __future__ import annotations

from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import Select, func, inspect, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.base.repository import IRepository
from app.core.errors import ConcurrencyError, ConflictError, DatabaseError, NotFoundError
from app.core.pagination import Page, PageRequest
from app.database.base import Entity

TEntity = TypeVar("TEntity", bound=Entity)


class SqlAlchemyRepository(IRepository[TEntity, int], Generic[TEntity]):
    """CRUD/query base bound to a single model type and an active session."""

    #: Columns (string) included in :class:`PageRequest`.search matching. Override per module.
    searchable_fields: ClassVar[tuple[str, ...]] = ()

    def __init__(self, model: type[TEntity], session: Session) -> None:
        self._model = model
        self._session = session
        self._columns: frozenset[str] = frozenset(inspect(model).columns.keys())

    # --- read -------------------------------------------------------------
    def get(self, entity_id: int, *, include_deleted: bool = False) -> TEntity | None:
        entity = self._session.get(self._model, entity_id)
        if entity is None:
            return None
        if not include_deleted and bool(getattr(entity, "is_deleted", False)):
            return None
        return entity

    def get_or_raise(self, entity_id: int, *, include_deleted: bool = False) -> TEntity:
        entity = self.get(entity_id, include_deleted=include_deleted)
        if entity is None:
            raise NotFoundError(
                f"{self._model.__name__} #{entity_id} was not found.",
                details={"model": self._model.__name__, "id": entity_id},
            )
        return entity

    def get_by_uuid(self, uuid: str, *, include_deleted: bool = False) -> TEntity | None:
        return self.find_one(include_deleted=include_deleted, uuid=uuid)

    def find(self, *, include_deleted: bool = False, **filters: Any) -> list[TEntity]:
        stmt = select(self._model).where(*self._conditions(include_deleted, filters, None))
        stmt = self._order_default(stmt)
        return list(self._session.execute(stmt).scalars().all())

    def find_one(self, *, include_deleted: bool = False, **filters: Any) -> TEntity | None:
        stmt = select(self._model).where(*self._conditions(include_deleted, filters, None)).limit(1)
        return self._session.execute(stmt).scalars().first()

    def list(self, request: PageRequest, *, include_deleted: bool = False) -> Page[TEntity]:
        conditions = self._conditions(include_deleted, request.filters, request.search)
        total = self._session.execute(
            select(func.count()).select_from(self._model).where(*conditions)
        ).scalar_one()
        if total == 0:
            return Page.empty(request)

        stmt = select(self._model).where(*conditions)
        stmt = self._apply_sort(stmt, request)
        stmt = stmt.offset(request.offset).limit(request.limit)
        items = list(self._session.execute(stmt).scalars().all())
        return Page(items=items, total=int(total), page=request.page, size=request.size)

    def count(self, *, include_deleted: bool = False, **filters: Any) -> int:
        conditions = self._conditions(include_deleted, filters, None)
        return int(
            self._session.execute(
                select(func.count()).select_from(self._model).where(*conditions)
            ).scalar_one()
        )

    def exists(self, *, include_deleted: bool = False, **filters: Any) -> bool:
        return self.count(include_deleted=include_deleted, **filters) > 0

    # --- write ------------------------------------------------------------
    def add(self, entity: TEntity) -> TEntity:
        self._session.add(entity)
        self._flush()
        return entity

    def update(self, entity: TEntity) -> TEntity:
        managed = self._ensure_attached(entity)
        self._flush()
        return managed

    def soft_delete(self, entity: TEntity, *, by: int | None = None) -> None:
        managed = self._ensure_attached(entity)
        managed.mark_deleted(by)
        self._flush()

    def restore(self, entity: TEntity, *, by: int | None = None) -> None:
        managed = self._ensure_attached(entity)
        managed.restore(by)
        self._flush()

    # --- query construction helpers --------------------------------------
    def _conditions(
        self, include_deleted: bool, filters: dict[str, Any], search: str | None
    ) -> list[Any]:
        conditions: list[Any] = []
        if not include_deleted:
            conditions.append(self._model.is_deleted.is_(False))
        for field_name, value in filters.items():
            conditions.append(self._column(field_name) == value)
        if search and self.searchable_fields:
            term = f"%{search}%"
            conditions.append(or_(*(self._column(f).ilike(term) for f in self.searchable_fields)))
        return conditions

    def _apply_sort(self, stmt: Select, request: PageRequest) -> Select:
        order_by = []
        for sort in request.sort:
            if sort.field not in self._columns:
                continue  # ignore unknown sort fields defensively
            column = self._column(sort.field)
            order_by.append(column.desc() if sort.direction.is_descending else column.asc())
        if not order_by:
            order_by.append(self._model.id.asc())  # deterministic pagination
        return stmt.order_by(*order_by)

    def _order_default(self, stmt: Select) -> Select:
        return stmt.order_by(self._model.id.asc())

    def _column(self, name: str) -> Any:
        if name not in self._columns:
            raise DatabaseError(
                f"Unknown field '{name}' on {self._model.__name__}.",
                details={"model": self._model.__name__, "field": name},
            )
        return getattr(self._model, name)

    def _ensure_attached(self, entity: TEntity) -> TEntity:
        if entity in self._session:
            return entity
        return self._session.merge(entity)

    def _flush(self) -> None:
        try:
            self._session.flush()
        except StaleDataError as exc:
            raise ConcurrencyError(
                "The record was modified by someone else. Reload and try again.", cause=exc
            ) from exc
        except IntegrityError as exc:
            raise ConflictError(
                "The operation violates a uniqueness or integrity constraint.",
                details={"reason": _orig(exc)},
                cause=exc,
            ) from exc
        except SQLAlchemyError as exc:
            raise DatabaseError("A database error occurred.", cause=exc) from exc


def _orig(exc: SQLAlchemyError) -> str:
    origin = getattr(exc, "orig", None)
    return str(origin) if origin is not None else exc.__class__.__name__
