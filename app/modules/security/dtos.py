"""Data transfer objects for the security module + ORM->DTO mappers.

DTOs are the only security types that cross the service boundary; ORM ``User``/``Role``
instances never escape a service (Part 2).
"""

from __future__ import annotations

from app.core.base.dto import BaseDTO
from app.modules.security.models.user import User


class LoginRequest(BaseDTO):
    username: str
    password: str


class CreateUserRequest(BaseDTO):
    username: str
    password: str
    full_name: str | None = None
    email: str | None = None
    role_codes: tuple[str, ...] = ()


class RoleDTO(BaseDTO):
    id: int
    code: str
    name: str


class UserDTO(BaseDTO):
    """Management projection of a user (no secrets)."""

    id: int
    uuid: str
    username: str
    full_name: str | None = None
    email: str | None = None
    is_active: bool = True
    is_locked: bool = False
    roles: tuple[str, ...] = ()


class AuthenticatedUser(BaseDTO):
    """The authenticated principal: identity + effective permissions for RBAC checks."""

    id: int
    uuid: str
    username: str
    full_name: str | None = None
    roles: tuple[str, ...] = ()
    permissions: frozenset[str] = frozenset()

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(code in self.permissions for code in codes)

    @property
    def display_name(self) -> str:
        return self.full_name or self.username


# --- mappers (called inside services while the session/relationships are loaded) ------------
def to_user_dto(user: User) -> UserDTO:
    return UserDTO(
        id=user.id,
        uuid=user.uuid,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        is_active=user.is_active,
        is_locked=user.is_locked,
        roles=tuple(sorted(user.role_codes)),
    )


def to_authenticated_user(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        uuid=user.uuid,
        username=user.username,
        full_name=user.full_name,
        roles=tuple(sorted(user.role_codes)),
        permissions=frozenset(user.permission_codes),
    )
