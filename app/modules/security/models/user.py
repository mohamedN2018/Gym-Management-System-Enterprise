"""User entity — an authenticatable account with assigned roles."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Entity
from app.modules.security.models.associations import user_roles
from app.modules.security.models.role import Role


class User(Entity):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    #: argon2id hash — never the plaintext password (Part 1).
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    #: A locked account cannot authenticate even with valid credentials.
    is_locked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin")

    @property
    def role_codes(self) -> set[str]:
        return {role.code for role in self.roles}

    @property
    def permission_codes(self) -> set[str]:
        """All permission codes granted via the user's roles (union)."""
        codes: set[str] = set()
        for role in self.roles:
            codes |= role.permission_codes
        return codes

    @property
    def can_authenticate(self) -> bool:
        return self.is_active and not self.is_locked and not self.is_deleted
