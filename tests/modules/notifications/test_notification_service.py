import pytest
from app.infrastructure import ApplicationContext
from app.modules.inventory.dtos import CreateProductRequest
from app.modules.inventory.services import ProductService
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.services import MemberService
from app.modules.membership.dtos import CreatePlanRequest, CreateSubscriptionRequest
from app.modules.membership.services import MembershipService
from app.modules.notifications.services import NotificationService

pytestmark = pytest.mark.integration


@pytest.fixture
def notifications(gym_context: ApplicationContext) -> NotificationService:
    return gym_context.container.resolve(NotificationService)


def test_no_alerts_initially(notifications):
    # Seeded products are above the low-stock threshold; no subscriptions exist yet.
    result = notifications.get_alerts()
    assert result.is_success
    assert result.value == []


def test_alerts_for_expiring_subscription_and_low_stock(gym_context, notifications):
    members = gym_context.container.resolve(MemberService)
    membership = gym_context.container.resolve(MembershipService)
    products = gym_context.container.resolve(ProductService)

    member = members.create_member(CreateMemberRequest(first_name="Soon")).value
    plan = membership.create_plan(CreatePlanRequest(name="Trial", price=0, duration_days=3)).value
    membership.subscribe(CreateSubscriptionRequest(member_id=member.id, plan_id=plan.id))
    products.create_product(CreateProductRequest(name="Rare", price=5, stock_quantity=2))

    result = notifications.get_alerts()
    assert result.is_success
    categories = {alert.category for alert in result.value}
    assert "membership" in categories  # expiring within 7 days
    assert "inventory" in categories  # stock 2 <= threshold
    assert notifications.count_alerts() >= 2
