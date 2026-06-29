"""Members module wiring — registers the member service in the DI container."""

from __future__ import annotations

from app.core.di import Container
from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY
from app.logs.logging_service import LoggingService
from app.modules.members.services import MemberService


def register_members_services(container: Container) -> None:
    container.register_factory(
        MemberService,
        lambda c: MemberService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
