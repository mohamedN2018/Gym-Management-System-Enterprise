"""Declarative base and the global :class:`Entity` mixin.

Every business table inherits :class:`Entity`, which supplies the mandatory global fields from
Part 3.1 (id, uuid, created_at, updated_at, created_by, updated_by, deleted_at, deleted_by,
is_deleted, is_active, version, remarks), soft-delete behavior, and optimistic-concurrency
versioning.

A constraint **naming convention** is configured on the metadata so Alembic autogenerate
produces stable, portable, deterministic names across SQLite and PostgreSQL.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, MetaData, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

#: Deterministic names for indexes/constraints (critical for portable migrations).
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _utcnow() -> datetime:
    """Timezone-aware UTC now (portable default for timestamp columns)."""
    return datetime.now(UTC)


def _new_uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Entity(Base):
    """Abstract base carrying the mandatory global fields and lifecycle behavior.

    ``created_by``/``updated_by``/``deleted_by`` reference ``users.id`` *logically*; the FK
    constraint is added once the users table exists (avoids a load-order/self-reference cycle).
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        String(36), default=_new_uuid, unique=True, index=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1"), nullable=False
    )

    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict:  # noqa: N805 - SQLAlchemy directive signature
        # Enables optimistic concurrency: UPDATEs are guarded by the version column and bump it.
        return {"version_id_col": cls.version}

    # --- lifecycle behavior ----------------------------------------------
    def mark_deleted(self, by: int | None = None) -> None:
        """Soft-delete this record (idempotent)."""
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = _utcnow()
        self.deleted_by = by

    def restore(self, by: int | None = None) -> None:
        """Reverse a soft delete."""
        self.is_deleted = False
        self.is_active = True
        self.deleted_at = None
        self.deleted_by = None
        self.updated_by = by

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} id={self.id} uuid={getattr(self, 'uuid', None)!r}>"
