"""Trainers module wiring."""

from __future__ import annotations

from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY
from app.logs.logging_service import LoggingService
from app.modules.trainers.services import TrainerService


def register_trainer_services(container) -> None:
    container.register_factory(
        TrainerService,
        lambda c: TrainerService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
