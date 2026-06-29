"""Inventory module wiring + startup seeding."""

from __future__ import annotations

from datetime import datetime

from app.core.events import EventBus
from app.infrastructure.bootstrap import UOW_FACTORY_KEY, ApplicationContext
from app.logs.logging_service import LoggingService
from app.modules.inventory.seed import seed_sample_products
from app.modules.inventory.services import PosService, ProductService
from app.modules.payments.services import PaymentService


def register_inventory_services(container) -> None:
    container.register_factory(
        ProductService,
        lambda c: ProductService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )
    container.register_factory(
        PosService,
        lambda c: PosService(
            uow_factory=c.resolve(UOW_FACTORY_KEY),
            payment_service=c.resolve(PaymentService),
            now_provider=datetime.now,
            events=c.resolve(EventBus),
            logging=c.resolve(LoggingService),
        ),
    )


def initialize_inventory(context: ApplicationContext) -> None:
    seed_sample_products(context.new_unit_of_work)
    register_inventory_services(context.container)
