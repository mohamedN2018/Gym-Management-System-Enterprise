"""Engine and session-factory construction.

Builds a SQLAlchemy engine from configuration. Defaults to a local SQLite file in the app data
directory; any explicit ``GYM_ERP_DATABASE__URL`` (e.g. PostgreSQL) is used verbatim, keeping
the upgrade path open without code changes.

SQLite is hardened for a desktop, multi-threaded application:
- ``foreign_keys=ON``     — enforce referential integrity (off by default in SQLite)
- ``journal_mode=WAL``    — concurrent readers alongside a writer; safer crash recovery
- ``synchronous=NORMAL``  — durable with WAL, much faster than FULL
- ``busy_timeout``        — wait instead of failing on transient write locks
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.core.constants import SQLITE_URL_SCHEME
from app.settings.config import AppConfig
from app.settings.paths import AppPaths

#: SQLite waits up to this long (ms) for a write lock before raising "database is locked".
_SQLITE_BUSY_TIMEOUT_MS = 5000


def build_database_url(config: AppConfig, paths: AppPaths) -> URL | str:
    """Return the configured database URL, or a local SQLite URL derived from ``paths``."""
    if config.database.url:
        return config.database.url
    return URL.create(SQLITE_URL_SCHEME, database=str(paths.database_file))


def is_sqlite_url(url: URL | str) -> bool:
    if isinstance(url, URL):
        return url.get_backend_name() == "sqlite"
    return str(url).startswith("sqlite")


def _install_sqlite_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record) -> None:  # pragma: no cover - driver cb
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
        finally:
            cursor.close()


def create_engine_and_session_factory(
    config: AppConfig, paths: AppPaths
) -> tuple[Engine, sessionmaker[Session]]:
    """Create the engine and a configured session factory.

    ``expire_on_commit=False`` keeps committed instances usable while they are mapped to DTOs;
    ``autoflush=False`` gives services explicit control over when SQL is emitted.
    """
    url = build_database_url(config, paths)
    sqlite = is_sqlite_url(url)

    connect_args: dict[str, object] = {}
    if sqlite:
        # Sessions are used from Qt worker threads (each with its own connection).
        connect_args["check_same_thread"] = False
        paths.database_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url, echo=config.database.echo, future=True, connect_args=connect_args)

    if sqlite:
        _install_sqlite_pragmas(engine)

    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, future=True
    )
    return engine, session_factory
