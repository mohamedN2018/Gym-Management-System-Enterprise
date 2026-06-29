"""Role entity — a named bundle of permissions assignable to users."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Entity
from app.modules.security.models.associations import role_permissions
from app.modules.security.models.permission import Permission


class Role(Entity):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: System roles are seeded and protected from deletion/renaming of their code.
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, lazy="selectin"
    )

    @property
    def permission_codes(self) -> set[str]:
        return {permission.code for permission in self.permissions}
