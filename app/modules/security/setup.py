"""Security module wiring + startup initialization.

``register_security_services`` registers the module's services in the DI container (resolving
their dependencies from the foundation services). ``initialize_security`` creates the schema
and seeds the RBAC baseline — call it once at application startup before showing the login.
"""

from __future__ import annotations

from app.core.di import Container
from app.core.events import EventBus
from app.database.schema import create_all
from app.infrastructure.bootstrap import UOW_FACTORY_KEY, ApplicationContext
from app.logs.logging_service import LoggingService
from app.modules.security.seed import SecuritySeeder
from app.modules.security.services import (
    AuthenticationService,
    AuthorizationService,
    UserService,
)
from app.security.password_hasher import PasswordHasher


def register_security_services(container: Container) -> None:
    """Register security services as singletons resolved from foundation dependencies."""
    container.register_factory(
        AuthenticationService,
        lambda c: AuthenticationService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            password_hasher=c.resolve(PasswordHasher),
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
    container.register_factory(
        AuthorizationService,
        lambda c: AuthorizationService(logging=c.resolve(LoggingService)),
    )
    container.register_factory(
        UserService,
        lambda c: UserService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            password_hasher=c.resolve(PasswordHasher),
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )


def initialize_security(context: ApplicationContext) -> None:
    """Create the schema and seed permissions/roles/admin, then register services."""
    create_all(context.engine)
    SecuritySeeder(
        uow_factory=context.new_unit_of_work,
        password_hasher=context.container.resolve(PasswordHasher),
        logging=context.logging,
    ).seed()
    register_security_services(context.container)
