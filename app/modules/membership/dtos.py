"""Membership DTOs + mappers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.base.dto import BaseDTO
from app.modules.membership.models.plan import MembershipPlan
from app.modules.membership.models.subscription import Subscription


class CreatePlanRequest(BaseDTO):
    name: str
    price: Decimal = Decimal("0")
    duration_days: int = 30
    description: str | None = None
    code: str | None = None


class PlanDTO(BaseDTO):
    id: int
    code: str
    name: str
    price: Decimal
    duration_days: int
    description: str | None = None
    is_active: bool = True


class CreateSubscriptionRequest(BaseDTO):
    member_id: int
    plan_id: int
    start_date: date | None = None


class SubscriptionDTO(BaseDTO):
    id: int
    member_id: int
    member_label: str
    plan_id: int
    plan_name: str
    start_date: date
    end_date: date
    price_paid: Decimal
    status: str


class ActiveSubscriptionDTO(BaseDTO):
    """Lightweight view of a member's currently-valid subscription."""

    plan_name: str
    end_date: date
    remaining_days: int


def to_plan_dto(plan: MembershipPlan) -> PlanDTO:
    return PlanDTO(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        price=plan.price,
        duration_days=plan.duration_days,
        description=plan.description,
        is_active=plan.is_active,
    )


def to_subscription_dto(subscription: Subscription, *, member_label: str) -> SubscriptionDTO:
    return SubscriptionDTO(
        id=subscription.id,
        member_id=subscription.member_id,
        member_label=member_label,
        plan_id=subscription.plan_id,
        plan_name=subscription.plan.name if subscription.plan else "",
        start_date=subscription.start_date,
        end_date=subscription.end_date,
        price_paid=subscription.price_paid,
        status=subscription.status,
    )
