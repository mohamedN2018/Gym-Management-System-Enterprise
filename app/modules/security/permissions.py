"""Permission & role catalog (the authoritative registry seeded into the database).

Defining capabilities as stable string codes lets services and UI check authorization without
magic strings scattered around (Part 1: *never hardcode values*). New modules extend
``ALL_PERMISSIONS``; the seeder reconciles the database to this catalog on startup.
"""

from __future__ import annotations

from dataclasses import dataclass


class Permissions:
    """Stable permission codes (``<area>.<action>``)."""

    DASHBOARD_VIEW = "dashboard.view"
    MEMBERS_VIEW = "members.view"
    MEMBERS_MANAGE = "members.manage"
    MEMBERSHIPS_VIEW = "memberships.view"
    MEMBERSHIPS_MANAGE = "memberships.manage"
    ATTENDANCE_VIEW = "attendance.view"
    ATTENDANCE_CHECKIN = "attendance.checkin"
    PAYMENTS_VIEW = "payments.view"
    TRAINERS_VIEW = "trainers.view"
    TRAINERS_MANAGE = "trainers.manage"
    INVENTORY_VIEW = "inventory.view"
    INVENTORY_MANAGE = "inventory.manage"
    POS_USE = "pos.use"
    REPORTS_VIEW = "reports.view"
    EMPLOYEES_VIEW = "employees.view"
    EMPLOYEES_MANAGE = "employees.manage"
    NOTIFICATIONS_VIEW = "notifications.view"
    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"
    ROLES_VIEW = "roles.view"
    ROLES_MANAGE = "roles.manage"
    AUDIT_VIEW = "audit.view"
    SETTINGS_MANAGE = "settings.manage"


class Roles:
    """Stable codes for the seeded system roles."""

    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    RECEPTIONIST = "receptionist"


@dataclass(frozen=True, slots=True)
class PermissionSpec:
    code: str
    name: str
    category: str


@dataclass(frozen=True, slots=True)
class RoleSpec:
    code: str
    name: str
    permissions: tuple[str, ...] = ()
    all_permissions: bool = False


#: The complete permission catalog. Extended as modules are added.
ALL_PERMISSIONS: tuple[PermissionSpec, ...] = (
    PermissionSpec(Permissions.DASHBOARD_VIEW, "View dashboard", "dashboard"),
    PermissionSpec(Permissions.MEMBERS_VIEW, "View members", "members"),
    PermissionSpec(Permissions.MEMBERS_MANAGE, "Create/edit members", "members"),
    PermissionSpec(Permissions.MEMBERSHIPS_VIEW, "View plans & subscriptions", "memberships"),
    PermissionSpec(Permissions.MEMBERSHIPS_MANAGE, "Manage plans & subscriptions", "memberships"),
    PermissionSpec(Permissions.ATTENDANCE_VIEW, "View attendance", "attendance"),
    PermissionSpec(Permissions.ATTENDANCE_CHECKIN, "Check members in", "attendance"),
    PermissionSpec(Permissions.PAYMENTS_VIEW, "View payments & revenue", "payments"),
    PermissionSpec(Permissions.TRAINERS_VIEW, "View trainers", "trainers"),
    PermissionSpec(Permissions.TRAINERS_MANAGE, "Create/edit trainers", "trainers"),
    PermissionSpec(Permissions.INVENTORY_VIEW, "View products", "inventory"),
    PermissionSpec(Permissions.INVENTORY_MANAGE, "Create/edit products", "inventory"),
    PermissionSpec(Permissions.POS_USE, "Use point of sale", "inventory"),
    PermissionSpec(Permissions.REPORTS_VIEW, "Export reports", "reports"),
    PermissionSpec(Permissions.EMPLOYEES_VIEW, "View employees", "employees"),
    PermissionSpec(Permissions.EMPLOYEES_MANAGE, "Create/edit employees", "employees"),
    PermissionSpec(Permissions.NOTIFICATIONS_VIEW, "View notifications", "notifications"),
    PermissionSpec(Permissions.USERS_VIEW, "View users", "users"),
    PermissionSpec(Permissions.USERS_MANAGE, "Create/edit users", "users"),
    PermissionSpec(Permissions.ROLES_VIEW, "View roles", "roles"),
    PermissionSpec(Permissions.ROLES_MANAGE, "Create/edit roles", "roles"),
    PermissionSpec(Permissions.AUDIT_VIEW, "View audit log", "audit"),
    PermissionSpec(Permissions.SETTINGS_MANAGE, "Manage settings", "settings"),
)

ALL_PERMISSION_CODES: tuple[str, ...] = tuple(spec.code for spec in ALL_PERMISSIONS)

#: Seeded system roles. The administrator implicitly receives every permission.
DEFAULT_ROLES: tuple[RoleSpec, ...] = (
    RoleSpec(Roles.ADMINISTRATOR, "Administrator", all_permissions=True),
    RoleSpec(
        Roles.MANAGER,
        "Manager",
        permissions=(
            Permissions.DASHBOARD_VIEW,
            Permissions.MEMBERS_VIEW,
            Permissions.MEMBERS_MANAGE,
            Permissions.MEMBERSHIPS_VIEW,
            Permissions.MEMBERSHIPS_MANAGE,
            Permissions.ATTENDANCE_VIEW,
            Permissions.ATTENDANCE_CHECKIN,
            Permissions.PAYMENTS_VIEW,
            Permissions.TRAINERS_VIEW,
            Permissions.TRAINERS_MANAGE,
            Permissions.INVENTORY_VIEW,
            Permissions.INVENTORY_MANAGE,
            Permissions.POS_USE,
            Permissions.REPORTS_VIEW,
            Permissions.EMPLOYEES_VIEW,
            Permissions.EMPLOYEES_MANAGE,
            Permissions.NOTIFICATIONS_VIEW,
            Permissions.USERS_VIEW,
            Permissions.AUDIT_VIEW,
        ),
    ),
    RoleSpec(
        Roles.RECEPTIONIST,
        "Receptionist",
        permissions=(
            Permissions.DASHBOARD_VIEW,
            Permissions.MEMBERS_VIEW,
            Permissions.MEMBERS_MANAGE,
            Permissions.MEMBERSHIPS_VIEW,
            Permissions.MEMBERSHIPS_MANAGE,
            Permissions.ATTENDANCE_VIEW,
            Permissions.ATTENDANCE_CHECKIN,
            Permissions.INVENTORY_VIEW,
            Permissions.POS_USE,
            Permissions.NOTIFICATIONS_VIEW,
        ),
    ),
)


def role_permission_codes(spec: RoleSpec) -> tuple[str, ...]:
    """Resolve the permission codes a role grants (``all_permissions`` expands to everything)."""
    return ALL_PERMISSION_CODES if spec.all_permissions else spec.permissions
