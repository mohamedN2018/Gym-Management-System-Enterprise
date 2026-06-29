"""ORM models for the security module.

Importing this package registers ``User``, ``Role``, ``Permission`` and the association
tables on the shared ``Base.metadata`` (used by schema creation and Alembic autogenerate).
"""

from app.modules.security.models.associations import role_permissions, user_roles
from app.modules.security.models.permission import Permission
from app.modules.security.models.role import Role
from app.modules.security.models.user import User

__all__ = ["Permission", "Role", "User", "role_permissions", "user_roles"]
