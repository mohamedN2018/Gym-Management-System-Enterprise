"""Point-of-sale service — checkout a cart into a sale, decrement stock, record payment."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from decimal import Decimal

from app.core.base.service import BaseService
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.events import Event, EventBus
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.inventory.dtos import CartLine, SaleDTO
from app.modules.inventory.events import InventoryEvents
from app.modules.inventory.models.sale import Sale, SaleItem
from app.modules.inventory.repositories import ProductRepository, SaleRepository
from app.modules.payments.dtos import RecordPaymentRequest
from app.modules.payments.models.payment import PaymentMethod, PaymentType
from app.modules.payments.services import PaymentService

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]
NowProvider = Callable[[], datetime]


class PosService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        payment_service: PaymentService,
        now_provider: NowProvider,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._payments = payment_service
        self._now = now_provider
        self._logging = logging

    def checkout(
        self,
        lines: Sequence[CartLine],
        *,
        method: str = PaymentMethod.CASH,
        created_by: int | None = None,
    ) -> Result[SaleDTO]:
        def _checkout() -> SaleDTO:
            if not lines:
                raise BusinessRuleError("The cart is empty.")
            with self._uow_factory() as uow:
                products = ProductRepository(uow.session)
                sale = Sale(
                    total=Decimal("0"), item_count=0, sold_at=self._now(), created_by=created_by
                )
                total = Decimal("0")
                count = 0
                for line in lines:
                    if line.quantity <= 0:
                        continue
                    product = products.get(line.product_id)
                    if product is None:
                        raise NotFoundError(
                            "Product not found.", details={"product_id": line.product_id}
                        )
                    if product.stock_quantity < line.quantity:
                        raise BusinessRuleError(
                            "Insufficient stock.",
                            details={"product": product.name, "available": product.stock_quantity},
                        )
                    line_total = product.price * line.quantity
                    sale.items.append(
                        SaleItem(
                            product_id=product.id,
                            quantity=line.quantity,
                            unit_price=product.price,
                            line_total=line_total,
                            created_by=created_by,
                        )
                    )
                    product.stock_quantity -= line.quantity
                    total += line_total
                    count += line.quantity
                if count == 0:
                    raise BusinessRuleError("The cart is empty.")
                sale.total = total
                sale.item_count = count
                SaleRepository(uow.session).add(sale)
                dto = SaleDTO(id=sale.id, total=sale.total, item_count=sale.item_count)
                uow.commit()

            self._payments.record_payment(
                RecordPaymentRequest(
                    amount=dto.total,
                    method=method,
                    payment_type=PaymentType.POS,
                    reference=f"SALE-{dto.id}",
                ),
                created_by=created_by,
            )
            if self._logging:
                self._logging.audit(
                    action="sale",
                    module="inventory",
                    result="success",
                    user=created_by,
                    new_value={"sale_id": dto.id, "total": str(dto.total)},
                )
            self._publish(
                Event(InventoryEvents.SALE_COMPLETED, {"sale_id": dto.id, "total": str(dto.total)})
            )
            return dto

        return self._guard(_checkout, message="Could not complete sale")
