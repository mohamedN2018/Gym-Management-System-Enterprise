"""Security module — users, roles, permissions (RBAC), authentication and authorization.

The gatekeeper module every other feature depends on. Provides:

- **Models:** :class:`User`, :class:`Role`, :class:`Permission` (+ association tables).
- **Services:** authentication (login), authorization (RBAC checks), user management.
- **Seeding:** default permission catalog, system roles, and an initial administrator.

It owns no UI business logic; the login dialog under ``ui/`` is presentation only.
"""
