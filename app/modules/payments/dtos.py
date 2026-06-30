"""Payment DTOs + mapper."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.core.base.dto import BaseDTO
from app.modules.payments.models.payment import Payment, PaymentMethod, PaymentType


class RecordPaymentRequest(BaseDTO):
    amount: Decimal
    member_id: int | None = None
    method: str = PaymentMethod.CASH
    payment_type: str = PaymentType.OTHER
    reference: str | None = None
    note: str | None = None


class PaymentDTO(BaseDTO):
    id: int
    member_id: int | None = None
    member_label: str = ""
    amount: Decimal
    method: str
    payment_type: str
    reference: str | None = None
    note: str | None = None
    paid_at: datetime


def to_payment_dto(payment: Payment, *, member_label: str = "") -> PaymentDTO:
    return PaymentDTO(
        id=payment.id,
        member_id=payment.member_id,
        member_label=member_label,
        amount=payment.amount,
        method=payment.method,
        payment_type=payment.payment_type,
        reference=payment.reference,
        note=payment.note,
        paid_at=payment.paid_at,
    )
