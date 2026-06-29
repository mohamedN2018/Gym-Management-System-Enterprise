"""Notification service — aggregates alerts from membership and inventory."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from app.core.base.service import BaseService
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.inventory.repositories import ProductRepository
from app.modules.members.repositories import MemberRepository
from app.modules.membership.repositories import SubscriptionRepository
from app.modules.notifications.dtos import AlertDTO, AlertSeverity

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]

#: Subscriptions ending within this many days are flagged.
EXPIRY_WINDOW_DAYS = 7
#: Products at or below this stock level are flagged.
LOW_STOCK_THRESHOLD = 10


class NotificationService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        today_provider: Callable[[], date],
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None)
        self._uow_factory = uow_factory
        self._today = today_provider

    def get_alerts(self) -> Result[list[AlertDTO]]:
        def _alerts() -> list[AlertDTO]:
            today = self._today()
            alerts: list[AlertDTO] = []
            with self._uow_factory() as uow:
                members = MemberRepository(uow.session)
                for sub in SubscriptionRepository(uow.session).expiring_within(
                    today, EXPIRY_WINDOW_DAYS
                ):
                    member = members.get(sub.member_id, include_deleted=True)
                    label = member.full_name if member else str(sub.member_id)
                    alerts.append(
                        AlertDTO(
                            category="membership",
                            severity=AlertSeverity.WARNING,
                            key="alerts.subscription_expiring",
                            params={"member": label, "days": str((sub.end_date - today).days)},
                        )
                    )
                for product in ProductRepository(uow.session).low_stock(LOW_STOCK_THRESHOLD):
                    alerts.append(
                        AlertDTO(
                            category="inventory",
                            severity=AlertSeverity.DANGER
                            if product.stock_quantity == 0
                            else AlertSeverity.WARNING,
                            key="alerts.low_stock",
                            params={"product": product.name, "stock": str(product.stock_quantity)},
                        )
                    )
            return alerts

        return self._guard(_alerts, message="Could not load alerts")

    def count_alerts(self) -> int:
        result = self.get_alerts()
        return len(result.value) if result.is_success else 0
