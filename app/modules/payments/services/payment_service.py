"""Payment service — record payments, list them, and report revenue."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.base.service import BaseService
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest, Sort
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.members.repositories import MemberRepository
from app.modules.payments.dtos import PaymentDTO, RecordPaymentRequest, to_payment_dto
from app.modules.payments.models.payment import Payment, PaymentMethod, PaymentType
from app.modules.payments.repositories import PaymentRepository

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]
NowProvider = Callable[[], datetime]

PAYMENT_RECORDED = "payments.payment.recorded"


class PaymentService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        now_provider: NowProvider,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._now = now_provider
        self._logging = logging

    def record_payment(
        self, request: RecordPaymentRequest, *, created_by: int | None = None
    ) -> Result[PaymentDTO]:
        def _record() -> PaymentDTO:
            with self._uow_factory() as uow:
                payment = Payment(
                    member_id=request.member_id,
                    amount=request.amount,
                    method=request.method,
                    payment_type=request.payment_type,
                    reference=request.reference,
                    note=request.note,
                    paid_at=self._now(),
                    created_by=created_by,
                )
                PaymentRepository(uow.session).add(payment)
                dto = to_payment_dto(payment)
                uow.commit()
            if self._logging:
                self._logging.audit(
                    action="payment",
                    module="payments",
                    result="success",
                    user=created_by,
                    new_value={"amount": str(dto.amount), "type": dto.payment_type},
                )
            self._publish(
                Event(PAYMENT_RECORDED, {"payment_id": dto.id, "amount": str(dto.amount)})
            )
            return dto

        return self._guard(_record, message="Could not record payment")

    def list_payments(self, request: PageRequest | None = None) -> Result[Page[PaymentDTO]]:
        def _list() -> Page[PaymentDTO]:
            with self._uow_factory() as uow:
                members = MemberRepository(uow.session)
                page = PaymentRepository(uow.session).list(
                    request or PageRequest(sort=(Sort.desc("paid_at"),))
                )
                items = []
                for payment in page.items:
                    label = ""
                    if payment.member_id is not None:
                        member = members.get(payment.member_id, include_deleted=True)
                        label = f"{member.membership_number} — {member.full_name}" if member else ""
                    items.append(to_payment_dto(payment, member_label=label))
                return Page(items=items, total=page.total, page=page.page, size=page.size)

        return self._guard(_list, message="Could not list payments")

    def total_revenue(self) -> Decimal:
        with self._uow_factory() as uow:
            return PaymentRepository(uow.session).total()

    def today_revenue(self) -> Decimal:
        now = self._now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        with self._uow_factory() as uow:
            return PaymentRepository(uow.session).total(start, start + timedelta(days=1))

    # --- event-driven recording ------------------------------------------
    def on_subscription_created(self, event: Event) -> None:
        """Record a subscription payment in reaction to the membership event."""
        amount = event.get("amount")
        if amount is None:
            return
        result = self.record_payment(
            RecordPaymentRequest(
                member_id=event.get("member_id"),
                amount=Decimal(str(amount)),
                method=PaymentMethod.CASH,
                payment_type=PaymentType.SUBSCRIPTION,
                reference=f"SUB-{event.get('subscription_id')}",
            )
        )
        if result.is_failure and self._logging:
            self._logging.get_logger(__name__).error(
                "Failed to auto-record subscription payment: %s", result.error
            )
