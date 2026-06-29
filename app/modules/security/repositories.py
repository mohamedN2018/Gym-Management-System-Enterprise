"""Repositories for the security module (persistence only — no business logic)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.security.models.permission import Permission
from app.modules.security.models.role import Role
from app.modules.security.models.user import User


class UserRepository(SqlAlchemyRepository[User]):
    searchable_fields = ("username", "full_name", "email")

    def __init__(self, session: Session) -> None:
        super().__init__(User, session)

    def find_by_username(self, username: str, *, include_deleted: bool = False) -> User | None:
        return self.find_one(include_deleted=include_deleted, username=username)


class RoleRepository(SqlAlchemyRepository[Role]):
    searchable_fields = ("code", "name")

    def __init__(self, session: Session) -> None:
        super().__init__(Role, session)

    def find_by_code(self, code: str) -> Role | None:
        return self.find_one(code=code)


class PermissionRepository(SqlAlchemyRepository[Permission]):
    searchable_fields = ("code", "name")

    def __init__(self, session: Session) -> None:
        super().__init__(Permission, session)

    def find_by_code(self, code: str) -> Permission | None:
        return self.find_one(code=code)
