"""Many-to-many association tables for RBAC.

These are pure link tables (composite PK of the two foreign keys) and intentionally do not
carry the full :class:`Entity` global fields — they record relationships, not business
entities. ``ON DELETE CASCADE`` keeps links consistent if a side is ever hard-removed.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Table

from app.database.base import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)
