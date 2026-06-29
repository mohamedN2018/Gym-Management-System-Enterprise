"""Payments module wiring — DI registration + event subscription."""

from __future__ import annotations

from datetime import datetime

from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY, ApplicationContext
from app.logs.logging_service import LoggingService
from app.modules.membership.events import MembershipEvents
from app.modules.payments.services import PaymentService


def register_payment_services(container) -> None:
    container.register_factory(
        PaymentService,
        lambda c: PaymentService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            now_provider=datetime.now,
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )


def initialize_payments(context: ApplicationContext) -> None:
    """Register the service and subscribe to subscription events (auto-record payments)."""
    register_payment_services(context.container)
    payment_service = context.container.resolve(PaymentService)
    context.events.subscribe(
        MembershipEvents.SUBSCRIPTION_CREATED, payment_service.on_subscription_created
    )
