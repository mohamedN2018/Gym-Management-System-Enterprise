"""Settings module wiring."""

from __future__ import annotations

from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY
from app.logs.logging_service import LoggingService
from app.modules.settings.services import SettingsService


def register_settings_services(container) -> None:
    container.register_factory(
        SettingsService,
        lambda c: SettingsService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
