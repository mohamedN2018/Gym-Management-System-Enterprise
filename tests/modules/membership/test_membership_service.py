from decimal import Decimal

import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.services import MemberService
from app.modules.membership.dtos import (
    CreatePlanRequest,
    CreateSubscriptionRequest,
    UpdatePlanRequest,
)
from app.modules.membership.services import MembershipService

pytestmark = pytest.mark.integration


@pytest.fixture
def membership(gym_context: ApplicationContext) -> MembershipService:
    return gym_context.container.resolve(MembershipService)


@pytest.fixture
def members(gym_context: ApplicationContext) -> MemberService:
    return gym_context.container.resolve(MemberService)


def _first_plan_id(membership: MembershipService) -> int:
    return membership.list_plans().value.items[0].id


def test_default_plans_are_seeded(membership):
    plans = membership.list_plans()
    assert plans.is_success
    codes = {plan.code for plan in plans.value.items}
    assert {"MONTHLY", "QUARTERLY", "YEARLY"} <= codes


def test_create_plan_autogenerates_code(membership):
    result = membership.create_plan(CreatePlanRequest(name="Day Pass", price=50, duration_days=1))
    assert result.is_success
    assert result.value.code.startswith("PLAN-")


def test_update_plan_changes_fields_but_not_code(membership):
    created = membership.create_plan(
        CreatePlanRequest(name="Bronze", price=40, duration_days=30)
    ).value

    result = membership.update_plan(
        created.id,
        UpdatePlanRequest(
            name="Bronze Plus", price=55, duration_days=45, description="Upgraded tier"
        ),
    )

    assert result.is_success
    assert result.value.code == created.code  # code is immutable
    assert result.value.name == "Bronze Plus"
    assert result.value.price == Decimal("55")
    assert result.value.duration_days == 45
    assert result.value.description == "Upgraded tier"


def test_update_unknown_plan_is_not_found(membership):
    result = membership.update_plan(
        999, UpdatePlanRequest(name="Ghost", price=10, duration_days=30)
    )
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_delete_plan_soft_deletes_and_hides_it(membership):
    created = membership.create_plan(
        CreatePlanRequest(name="Trial", price=0, duration_days=7)
    ).value

    result = membership.delete_plan(created.id)

    assert result.is_success
    remaining = {plan.id for plan in membership.list_plans().value.items}
    assert created.id not in remaining


def test_delete_unknown_plan_is_not_found(membership):
    result = membership.delete_plan(999)
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_subscribe_creates_active_subscription(members, membership):
    member = members.create_member(CreateMemberRequest(first_name="Nour")).value
    plans = membership.list_plans().value.items
    monthly = next(p for p in plans if p.code == "MONTHLY")

    result = membership.subscribe(
        CreateSubscriptionRequest(member_id=member.id, plan_id=monthly.id)
    )
    assert result.is_success
    assert result.value.status == "active"
    assert (result.value.end_date - result.value.start_date).days == monthly.duration_days

    active = membership.active_subscription(member.id)
    assert active.is_success
    assert active.value is not None
    assert active.value.remaining_days == monthly.duration_days
    assert membership.count_active_subscriptions() == 1


def test_subscribe_unknown_member_is_not_found(membership):
    result = membership.subscribe(
        CreateSubscriptionRequest(member_id=999, plan_id=_first_plan_id(membership))
    )
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_member_without_subscription_has_none(members, membership):
    member = members.create_member(CreateMemberRequest(first_name="Idle")).value
    active = membership.active_subscription(member.id)
    assert active.is_success
    assert active.value is None


def _subscribe(members, membership):
    member = members.create_member(CreateMemberRequest(first_name="Sub")).value
    plan_id = _first_plan_id(membership)
    return membership.subscribe(
        CreateSubscriptionRequest(member_id=member.id, plan_id=plan_id)
    ).value, member


def test_cancel_subscription_marks_cancelled_and_frees_active_count(members, membership):
    sub, member = _subscribe(members, membership)
    assert membership.count_active_subscriptions() == 1

    result = membership.cancel_subscription(sub.id)
    assert result.is_success
    assert result.value.status == "cancelled"
    assert membership.active_subscription(member.id).value is None
    assert membership.count_active_subscriptions() == 0


def test_cancel_already_cancelled_conflicts(members, membership):
    sub, _member = _subscribe(members, membership)
    assert membership.cancel_subscription(sub.id).is_success
    second = membership.cancel_subscription(sub.id)
    assert second.is_failure
    assert second.error.code is ErrorCode.CONFLICT


def test_cancel_unknown_subscription_is_not_found(membership):
    result = membership.cancel_subscription(999)
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_delete_subscription_soft_deletes_and_hides_it(members, membership):
    sub, _member = _subscribe(members, membership)
    result = membership.delete_subscription(sub.id)
    assert result.is_success
    remaining = {s.id for s in membership.list_subscriptions().value.items}
    assert sub.id not in remaining


def test_delete_unknown_subscription_is_not_found(membership):
    result = membership.delete_subscription(999)
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND
