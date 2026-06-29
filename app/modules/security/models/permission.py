"""Permission entity — a single, fine-grained capability (e.g. ``users.manage``)."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Entity


class Permission(Entity):
    __tablename__ = "permissions"

    #: Stable machine code used in authorization checks (unique).
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    #: Human-readable name (English; localized labels are resolved in the UI).
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Grouping for display (e.g. "users", "reports").
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
