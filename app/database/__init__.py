"""Persistence infrastructure (Infrastructure layer).

- :mod:`app.database.base`         — :class:`Base` declarative class + :class:`Entity` (globals)
- :mod:`app.database.engine`       — engine & session-factory construction (SQLite + PG-ready)
- :mod:`app.database.unit_of_work` — :class:`SqlAlchemyUnitOfWork`
- :mod:`app.database.repository`   — :class:`SqlAlchemyRepository` (generic CRUD/query base)
"""

from app.database.base import Base, Entity
from app.database.engine import (
    build_database_url,
    create_engine_and_session_factory,
    is_sqlite_url,
)
from app.database.repository import SqlAlchemyRepository
from app.database.unit_of_work import SqlAlchemyUnitOfWork, UnitOfWorkFactory

__all__ = [
    "Base",
    "Entity",
    "SqlAlchemyRepository",
    "SqlAlchemyUnitOfWork",
    "UnitOfWorkFactory",
    "build_database_url",
    "create_engine_and_session_factory",
    "is_sqlite_url",
]
