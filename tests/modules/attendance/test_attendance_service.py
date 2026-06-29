import pytest
from app.infrastructure import ApplicationContext
from app.modules.attendance.services import AttendanceService
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.services import MemberService
from app.modules.membership.dtos import CreateSubscriptionRequest
from app.modules.membership.services import MembershipService

pytestmark = pytest.mark.integration


@pytest.fixture
def attendance(gym_context: ApplicationContext) -> AttendanceService:
    return gym_context.container.resolve(AttendanceService)


@pytest.fixture
def members(gym_context: ApplicationContext) -> MemberService:
    return gym_context.container.resolve(MemberService)


@pytest.fixture
def membership(gym_context: ApplicationContext) -> MembershipService:
    return gym_context.container.resolve(MembershipService)


def _subscribed_member(members: MemberService, membership: MembershipService) -> str:
    member = members.create_member(CreateMemberRequest(first_name="Active")).value
    plan_id = membership.list_plans().value.items[0].id
    membership.subscribe(CreateSubscriptionRequest(member_id=member.id, plan_id=plan_id))
    return member.membership_number


def test_check_in_allowed_for_active_member(members, membership, attendance):
    number = _subscribed_member(members, membership)
    result = attendance.check_in(number)
    assert result.is_success
    assert result.value.allowed is True
    assert result.value.reason == "ok"
    assert result.value.remaining_days is not None
    assert attendance.today_count() == 1


def test_check_in_unknown_member_rejected(attendance):
    result = attendance.check_in("UNKNOWN")
    assert result.is_success
    assert result.value.allowed is False
    assert result.value.reason == "not_found"
    assert attendance.today_count() == 0  # not_found is not recorded


def test_check_in_without_subscription_rejected(members, attendance):
    member = members.create_member(CreateMemberRequest(first_name="NoSub")).value
    result = attendance.check_in(member.membership_number)
    assert result.is_success
    assert result.value.allowed is False
    assert result.value.reason == "no_active_subscription"
    # Rejected-but-known attempts are recorded for audit, but not counted as allowed entries.
    assert attendance.today_count() == 0


def test_list_today_includes_checkins(members, membership, attendance):
    number = _subscribed_member(members, membership)
    attendance.check_in(number)
    today = attendance.list_today()
    assert today.is_success
    assert len(today.value) == 1
    assert today.value[0].allowed is True
