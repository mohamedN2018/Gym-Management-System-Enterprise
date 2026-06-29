"""Payment repository (persistence only)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.payments.models.payment import Payment


class PaymentRepository(SqlAlchemyRepository[Payment]):
    searchable_fields = ("reference", "method", "payment_type")

    def __init__(self, session: Session) -> None:
        super().__init__(Payment, session)

    def total(self, start: datetime | None = None, end: datetime | None = None) -> Decimal:
        conditions = [Payment.is_deleted.is_(False)]
        if start is not None:
            conditions.append(Payment.paid_at >= start)
        if end is not None:
            conditions.append(Payment.paid_at < end)
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(*conditions)
        return Decimal(str(self._session.execute(stmt).scalar_one()))
