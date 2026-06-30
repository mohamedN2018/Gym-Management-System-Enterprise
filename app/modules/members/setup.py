"""Members module wiring — registers the member service in the DI container."""

from __future__ import annotations

from datetime import datetime

from app.core.di import Container
from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY
from app.logs.logging_service import LoggingService
from app.modules.members.services import MeasurementService, MemberService


def register_members_services(container: Container) -> None:
    container.register_factory(
        MemberService,
        lambda c: MemberService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
    container.register_factory(
        MeasurementService,
        lambda c: MeasurementService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            now_provider=datetime.now,
            logging=c.resolve(LoggingService),
        ),
    )
