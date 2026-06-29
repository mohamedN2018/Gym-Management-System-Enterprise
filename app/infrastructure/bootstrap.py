"""Application composition root.

Builds the dependency graph once, in dependency order, and returns an
:class:`ApplicationContext` exposing the wired singletons plus a :class:`Container` for
resolving services. The UI and (future) business modules consume this context — they never
construct infrastructure themselves.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.di import Container
from app.core.events import EventBus
from app.database.engine import create_engine_and_session_factory
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.localization.localization_service import LocalizationService
from app.logs.logging_service import LoggingService
from app.security.encryption import EncryptionService
from app.security.password_hasher import PasswordHasher
from app.services.qr_code_service import QrCodeService
from app.settings import AppConfig, AppPaths, load_config

#: DI token for the unit-of-work factory (a no-arg callable returning a fresh UoW).
UOW_FACTORY_KEY = "uow_factory"


@dataclass(frozen=True, slots=True)
class ApplicationContext:
    """The fully wired application runtime."""

    container: Container
    config: AppConfig
    paths: AppPaths
    logging: LoggingService
    events: EventBus
    localization: LocalizationService
    engine: Engine
    session_factory: sessionmaker[Session]

    def new_unit_of_work(self) -> SqlAlchemyUnitOfWork:
        """Create a fresh transactional unit of work."""
        return SqlAlchemyUnitOfWork(self.session_factory)

    def verify_database(self) -> bool:
        """Return ``True`` if the database accepts a trivial query (connectivity probe)."""
        log = self.logging.get_logger("app.infrastructure.bootstrap")
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            log.exception("Database connectivity check failed.")
            return False

    def dispose(self) -> None:
        """Release infrastructure resources (called at shutdown)."""
        self.engine.dispose()


def bootstrap(config: AppConfig | None = None) -> ApplicationContext:
    """Construct and wire the application runtime.

    Args:
        config: Optional pre-built configuration (tests inject overrides); otherwise loaded
            from environment/.env with safe offline defaults.
    """
    config = config or load_config()

    # 1) Filesystem layout (created if missing).
    paths = AppPaths.resolve(config.data_dir).ensure()

    # 2) Logging first, so every later step can report failures.
    logging_service = LoggingService().configure(paths=paths, level=config.logging.level)
    log = logging_service.get_logger("app.infrastructure.bootstrap")
    log.info(
        "Bootstrapping %s in %s mode (data dir: %s)",
        config.environment,
        config.language,
        paths.data_dir,
    )

    # 3) Event bus, with handler errors routed to logging.
    events = EventBus(on_handler_error=logging_service.on_event_handler_error)

    # 4) Localization (active language taken from configuration).
    localization = LocalizationService.default(default_language=config.language)

    # 6) Persistence.
    engine, session_factory = create_engine_and_session_factory(config, paths)

    # 7) Security primitives.
    password_hasher = PasswordHasher()
    encryption = EncryptionService.from_key_file(paths.encryption_key_file)

    # 8) Register everything for dependency injection.
    container = Container()
    container.register_instance(AppConfig, config)
    container.register_instance(AppPaths, paths)
    container.register_instance(LoggingService, logging_service)
    container.register_instance(EventBus, events)
    container.register_instance(LocalizationService, localization)
    container.register_instance(Engine, engine)
    container.register_instance(PasswordHasher, password_hasher)
    container.register_instance(EncryptionService, encryption)
    container.register_instance(QrCodeService, QrCodeService())
    container.register_factory(
        SqlAlchemyUnitOfWork,
        lambda _c: SqlAlchemyUnitOfWork(session_factory),
        singleton=False,
    )
    container.register_instance(UOW_FACTORY_KEY, lambda: SqlAlchemyUnitOfWork(session_factory))

    context = ApplicationContext(
        container=container,
        config=config,
        paths=paths,
        logging=logging_service,
        events=events,
        localization=localization,
        engine=engine,
        session_factory=session_factory,
    )
    container.register_instance(ApplicationContext, context)
    log.info("Bootstrap complete.")
    return context
