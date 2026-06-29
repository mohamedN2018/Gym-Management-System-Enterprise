from decimal import Decimal

import pytest
from app.infrastructure import ApplicationContext
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.services import MemberService
from app.modules.membership.dtos import CreateSubscriptionRequest
from app.modules.membership.services import MembershipService
from app.modules.payments.dtos import RecordPaymentRequest
from app.modules.payments.models.payment import PaymentType
from app.modules.payments.services import PaymentService

pytestmark = pytest.mark.integration


@pytest.fixture
def payments(gym_context: ApplicationContext) -> PaymentService:
    return gym_context.container.resolve(PaymentService)


def test_record_payment_updates_revenue(payments):
    assert payments.record_payment(RecordPaymentRequest(amount=Decimal("100.00"))).is_success
    assert payments.total_revenue() == Decimal("100.00")
    assert payments.today_revenue() == Decimal("100.00")


def test_subscription_payment_is_recorded_via_event(gym_context, payments):
    members = gym_context.container.resolve(MemberService)
    membership = gym_context.container.resolve(MembershipService)
    member = members.create_member(CreateMemberRequest(first_name="Payer")).value
    monthly = next(p for p in membership.list_plans().value.items if p.code == "MONTHLY")

    assert membership.subscribe(
        CreateSubscriptionRequest(member_id=member.id, plan_id=monthly.id)
    ).is_success

    # The payments module reacted to SUBSCRIPTION_CREATED and recorded the plan price.
    assert payments.total_revenue() == monthly.price
    listing = payments.list_payments()
    assert listing.is_success
    assert listing.value.total == 1
    assert listing.value.items[0].payment_type == PaymentType.SUBSCRIPTION
