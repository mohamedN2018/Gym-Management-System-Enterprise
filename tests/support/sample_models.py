"""Throwaway ORM model + repository used to exercise the persistence infrastructure.

Kept in the test support package (not in ``app``) so production code carries no test-only
entities. ``sku`` is unique to drive conflict tests.
"""

from __future__ import annotations

from app.database.base import Entity
from app.database.repository import SqlAlchemyRepository
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class Widget(Entity):
    __tablename__ = "test_widgets"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class WidgetRepository(SqlAlchemyRepository[Widget]):
    searchable_fields = ("name", "sku")

    def __init__(self, session) -> None:
        super().__init__(Widget, session)
