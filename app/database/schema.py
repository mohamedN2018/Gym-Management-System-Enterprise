"""Schema creation for the embedded database.

Imports every module's models (so they register on ``Base.metadata``) and creates any missing
tables. ``create_all`` is idempotent — existing tables are left untouched — which suits a local
SQLite desktop install. Schema *evolution* over releases is handled by Alembic migrations.

As new business modules are added, register their model packages in ``import_models``.
"""

from __future__ import annotations

from sqlalchemy import Engine

from app.database.base import Base


def import_models() -> None:
    """Import all model packages so their tables are registered on ``Base.metadata``."""
    import app.modules.attendance.models
    import app.modules.employees.models
    import app.modules.expenses.models
    import app.modules.inventory.models
    import app.modules.members.models
    import app.modules.membership.models
    import app.modules.payments.models
    import app.modules.security.models
    import app.modules.settings.models
    import app.modules.trainers.models  # noqa: F401


def create_all(engine: Engine) -> None:
    """Create any tables that do not yet exist."""
    import_models()
    Base.metadata.create_all(engine)
