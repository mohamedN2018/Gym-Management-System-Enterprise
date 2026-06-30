"""Membership service — plans and subscriptions (business rules + transactions)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from app.core.base.service import BaseService
from app.core.errors import ConflictError, NotFoundError
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest, Sort
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.members.repositories import MemberRepository
from app.modules.membership.dtos import (
    ActiveSubscriptionDTO,
    CreatePlanRequest,
    CreateSubscriptionRequest,
    PlanDTO,
    SubscriptionDTO,
    UpdatePlanRequest,
    to_plan_dto,
    to_subscription_dto,
)
from app.modules.membership.events import MembershipEvents
from app.modules.membership.models.plan import MembershipPlan
from app.modules.membership.models.subscription import Subscription, SubscriptionStatus
from app.modules.membership.repositories import PlanRepository, SubscriptionRepository
from app.modules.membership.validators import CreatePlanValidator

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


class MembershipService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        today_provider: Callable[[], date],
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._today = today_provider
        self._logging = logging
        self._plan_validator = CreatePlanValidator()

    # --- plans ------------------------------------------------------------
    def create_plan(
        self, request: CreatePlanRequest, *, created_by: int | None = None
    ) -> Result[PlanDTO]:
        def _create() -> PlanDTO:
            self._plan_validator.validate_and_raise(request)
            with self._uow_factory() as uow:
                repo = PlanRepository(uow.session)
                code = (
                    request.code or ""
                ).strip() or f"PLAN-{repo.count(include_deleted=True) + 1:03d}"
                if repo.find_by_code(code) is not None:
                    raise ConflictError("Plan code already exists.", details={"code": code})
                plan = MembershipPlan(
                    code=code,
                    name=request.name.strip(),
                    price=request.price,
                    duration_days=request.duration_days,
                    description=(request.description or None),
                    created_by=created_by,
                )
                repo.add(plan)
                dto = to_plan_dto(plan)
                uow.commit()
            self._publish(
                Event(MembershipEvents.PLAN_CREATED, {"plan_id": dto.id, "code": dto.code})
            )
            return dto

        return self._guard(_create, message="Could not create plan")

    def list_plans(self, request: PageRequest | None = None) -> Result[Page[PlanDTO]]:
        def _list() -> Page[PlanDTO]:
            with self._uow_factory() as uow:
                page = PlanRepository(uow.session).list(
                    request or PageRequest(sort=(Sort.asc("name"),))
                )
                return Page(
                    items=[to_plan_dto(p) for p in page.items],
                    total=page.total,
                    page=page.page,
                    size=page.size,
                )

        return self._guard(_list, message="Could not list plans")

    def update_plan(
        self, plan_id: int, request: UpdatePlanRequest, *, updated_by: int | None = None
    ) -> Result[PlanDTO]:
        def _update() -> PlanDTO:
            self._plan_validator.validate_and_raise(request)
            with self._uow_factory() as uow:
                repo = PlanRepository(uow.session)
                plan = repo.get_or_raise(plan_id)
                plan.name = request.name.strip()
                plan.price = request.price
                plan.duration_days = request.duration_days
                plan.description = (request.description or "").strip() or None
                plan.updated_by = updated_by
                repo.update(plan)
                dto = to_plan_dto(plan)
                uow.commit()
            self._publish(
                Event(MembershipEvents.PLAN_UPDATED, {"plan_id": dto.id, "code": dto.code})
            )
            return dto

        return self._guard(_update, message="Could not update plan")

    def delete_plan(self, plan_id: int, *, deleted_by: int | None = None) -> Result[None]:
        def _delete() -> None:
            with self._uow_factory() as uow:
                repo = PlanRepository(uow.session)
                plan = repo.get_or_raise(plan_id)
                repo.soft_delete(plan, by=deleted_by)
                uow.commit()
            self._publish(Event(MembershipEvents.PLAN_DELETED, {"plan_id": plan_id}))

        return self._guard(_delete, message="Could not delete plan")

    # --- subscriptions ----------------------------------------------------
    def subscribe(
        self, request: CreateSubscriptionRequest, *, created_by: int | None = None
    ) -> Result[SubscriptionDTO]:
        def _subscribe() -> SubscriptionDTO:
            with self._uow_factory() as uow:
                members = MemberRepository(uow.session)
                plans = PlanRepository(uow.session)
                subs = SubscriptionRepository(uow.session)

                member = members.get(request.member_id)
                if member is None:
                    raise NotFoundError(
                        "Member not found.", details={"member_id": request.member_id}
                    )
                plan = plans.get(request.plan_id)
                if plan is None:
                    raise NotFoundError("Plan not found.", details={"plan_id": request.plan_id})

                start = request.start_date or self._today()
                end = start + timedelta(days=plan.duration_days)
                subscription = Subscription(
                    member_id=member.id,
                    plan_id=plan.id,
                    start_date=start,
                    end_date=end,
                    price_paid=plan.price,
                    status=SubscriptionStatus.ACTIVE,
                    created_by=created_by,
                )
                subs.add(subscription)
                label = f"{member.membership_number} — {member.full_name}"
                dto = to_subscription_dto(subscription, member_label=label)
                uow.commit()
            self._publish(
                Event(
                    MembershipEvents.SUBSCRIPTION_CREATED,
                    {
                        "subscription_id": dto.id,
                        "member_id": dto.member_id,
                        "amount": str(dto.price_paid),
                    },
                )
            )
            return dto

        return self._guard(_subscribe, message="Could not create subscription")

    def list_subscriptions(
        self, request: PageRequest | None = None
    ) -> Result[Page[SubscriptionDTO]]:
        def _list() -> Page[SubscriptionDTO]:
            with self._uow_factory() as uow:
                members = MemberRepository(uow.session)
                page = SubscriptionRepository(uow.session).list(
                    request or PageRequest(sort=(Sort.desc("end_date"),))
                )
                items = []
                for sub in page.items:
                    member = members.get(sub.member_id, include_deleted=True)
                    label = (
                        f"{member.membership_number} — {member.full_name}"
                        if member
                        else str(sub.member_id)
                    )
                    items.append(to_subscription_dto(sub, member_label=label))
                return Page(items=items, total=page.total, page=page.page, size=page.size)

        return self._guard(_list, message="Could not list subscriptions")

    def cancel_subscription(
        self, subscription_id: int, *, updated_by: int | None = None
    ) -> Result[SubscriptionDTO]:
        def _cancel() -> SubscriptionDTO:
            with self._uow_factory() as uow:
                members = MemberRepository(uow.session)
                subs = SubscriptionRepository(uow.session)
                subscription = subs.get_or_raise(subscription_id)
                if subscription.status == SubscriptionStatus.CANCELLED:
                    raise ConflictError(
                        "Subscription is already cancelled.",
                        details={"subscription_id": subscription_id},
                    )
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.updated_by = updated_by
                subs.update(subscription)
                member = members.get(subscription.member_id, include_deleted=True)
                label = (
                    f"{member.membership_number} — {member.full_name}"
                    if member
                    else str(subscription.member_id)
                )
                dto = to_subscription_dto(subscription, member_label=label)
                uow.commit()
            self._publish(
                Event(
                    MembershipEvents.SUBSCRIPTION_CANCELLED,
                    {"subscription_id": dto.id, "member_id": dto.member_id},
                )
            )
            return dto

        return self._guard(_cancel, message="Could not cancel subscription")

    def delete_subscription(
        self, subscription_id: int, *, deleted_by: int | None = None
    ) -> Result[None]:
        def _delete() -> None:
            with self._uow_factory() as uow:
                subs = SubscriptionRepository(uow.session)
                subscription = subs.get_or_raise(subscription_id)
                subs.soft_delete(subscription, by=deleted_by)
                uow.commit()
            self._publish(
                Event(MembershipEvents.SUBSCRIPTION_DELETED, {"subscription_id": subscription_id})
            )

        return self._guard(_delete, message="Could not delete subscription")

    def active_subscription(self, member_id: int) -> Result[ActiveSubscriptionDTO | None]:
        def _active() -> ActiveSubscriptionDTO | None:
            today = self._today()
            with self._uow_factory() as uow:
                sub = SubscriptionRepository(uow.session).active_for_member(member_id, today)
                if sub is None:
                    return None
                return ActiveSubscriptionDTO(
                    plan_name=sub.plan.name if sub.plan else "",
                    end_date=sub.end_date,
                    remaining_days=(sub.end_date - today).days,
                )

        return self._guard(_active, message="Could not check subscription")

    def count_active_subscriptions(self) -> int:
        with self._uow_factory() as uow:
            return SubscriptionRepository(uow.session).count_active(self._today())
