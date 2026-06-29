"""Idempotent seeding of the RBAC baseline.

On startup the database is reconciled to the permission/role catalog and, on a fresh install,
a default administrator is created so the application can be logged into. Running it repeatedly
is safe: missing permissions/roles are added and system-role permission sets are refreshed.

The default administrator credentials are an *initial* secret intended to be changed on first
login (a guided first-run flow is a later enhancement); a warning is logged when created.
"""

from __future__ import annotations

from collections.abc import Callable

from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.security.models.permission import Permission
from app.modules.security.models.role import Role
from app.modules.security.models.user import User
from app.modules.security.permissions import (
    ALL_PERMISSIONS,
    DEFAULT_ROLES,
    Roles,
    role_permission_codes,
)
from app.modules.security.repositories import (
    PermissionRepository,
    RoleRepository,
    UserRepository,
)
from app.security.password_hasher import PasswordHasher

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]

#: Initial administrator credentials (change on first login).
SEED_ADMIN_USERNAME = "admin"
SEED_ADMIN_PASSWORD = "admin12345"
SEED_ADMIN_FULL_NAME = "System Administrator"


class SecuritySeeder:
    """Reconciles permissions/roles and ensures an initial administrator exists."""

    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        password_hasher: PasswordHasher,
        logging: LoggingService | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._hasher = password_hasher
        self._log = logging.get_logger(__name__) if logging else None

    def seed(self) -> None:
        with self._uow_factory() as uow:
            permissions = PermissionRepository(uow.session)
            roles = RoleRepository(uow.session)
            users = UserRepository(uow.session)

            by_code = self._sync_permissions(permissions)
            self._sync_roles(roles, by_code)
            self._ensure_admin(users, roles)

            uow.commit()

    def _sync_permissions(self, repo: PermissionRepository) -> dict[str, Permission]:
        by_code = {perm.code: perm for perm in repo.find(include_deleted=True)}
        for spec in ALL_PERMISSIONS:
            existing = by_code.get(spec.code)
            if existing is None:
                created = Permission(code=spec.code, name=spec.name, category=spec.category)
                repo.add(created)
                by_code[spec.code] = created
            else:
                existing.name = spec.name
                existing.category = spec.category
        return by_code

    def _sync_roles(self, repo: RoleRepository, by_code: dict[str, Permission]) -> None:
        for spec in DEFAULT_ROLES:
            granted = [by_code[code] for code in role_permission_codes(spec) if code in by_code]
            role = repo.find_by_code(spec.code)
            if role is None:
                role = Role(code=spec.code, name=spec.name, is_system=True)
                role.permissions = granted
                repo.add(role)
            else:
                role.name = spec.name
                role.is_system = True
                role.permissions = granted

    def _ensure_admin(self, users: UserRepository, roles: RoleRepository) -> None:
        if users.count(include_deleted=True) > 0:
            return  # an account already exists; never auto-create on an existing install
        admin_role = roles.find_by_code(Roles.ADMINISTRATOR)
        admin = User(
            username=SEED_ADMIN_USERNAME,
            password_hash=self._hasher.hash(SEED_ADMIN_PASSWORD),
            full_name=SEED_ADMIN_FULL_NAME,
        )
        if admin_role is not None:
            admin.roles = [admin_role]
        users.add(admin)
        if self._log:
            self._log.warning(
                "Created default administrator '%s'. Change this password on first login.",
                SEED_ADMIN_USERNAME,
            )
