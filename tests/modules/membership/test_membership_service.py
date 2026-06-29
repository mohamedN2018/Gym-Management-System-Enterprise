import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.services import MemberService
from app.modules.membership.dtos import CreatePlanRequest, CreateSubscriptionRequest
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
