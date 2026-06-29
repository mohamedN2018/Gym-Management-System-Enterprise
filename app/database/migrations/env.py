"""Alembic migration environment.

Resolves the database URL from the application's own configuration (so migrations target the
same local SQLite file the app uses, or a configured PostgreSQL URL) and enables SQLite-safe
*batch* ALTER operations plus type comparison for reliable autogenerate.

When a new business module is added, import its model package below so ``alembic revision
--autogenerate`` can see the tables. (No business models exist yet at the foundation milestone.)
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from app.database.base import Base
from app.database.engine import build_database_url, create_engine_and_session_factory
from app.settings import AppPaths, load_config

# --- model registration (extend as modules are built) ----------------------
# Example once the users module lands:
#     import app.modules.security.users.models
# ----------------------------------------------------------------------------

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to a script without a live DB connection."""
    app_config = load_config()
    paths = AppPaths.resolve(app_config.data_dir).ensure()
    url = str(build_database_url(app_config, paths))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    app_config = load_config()
    paths = AppPaths.resolve(app_config.data_dir).ensure()
    engine, _ = create_engine_and_session_factory(app_config, paths)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
