"""Membership module wiring + startup seeding."""

from __future__ import annotations

from datetime import date

from app.core.di import Container
from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY, ApplicationContext
from app.logs.logging_service import LoggingService
from app.modules.membership.seed import seed_default_plans
from app.modules.membership.services import MembershipService


def register_membership_services(container: Container) -> None:
    container.register_factory(
        MembershipService,
        lambda c: MembershipService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            today_provider=date.today,
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )


def initialize_membership(context: ApplicationContext) -> None:
    """Seed default plans and register the membership service. Schema is created globally."""
    seed_default_plans(context.new_unit_of_work)
    register_membership_services(context.container)
