"""Notifications module wiring."""

from __future__ import annotations

from datetime import date

from app.core.di import Container
from app.infrastructure.bootstrap import UOW_FACTORY_KEY
from app.logs.logging_service import LoggingService
from app.modules.notifications.services import NotificationService


def register_notification_services(container: Container) -> None:
    container.register_factory(
        NotificationService,
        lambda c: NotificationService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            today_provider=date.today,
            logging=c.resolve(LoggingService),
        ),
    )
