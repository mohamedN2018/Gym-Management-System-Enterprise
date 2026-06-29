from decimal import Decimal

import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.inventory.dtos import CartLine, CreateProductRequest
from app.modules.inventory.repositories import ProductRepository
from app.modules.inventory.services import PosService, ProductService
from app.modules.payments.services import PaymentService

pytestmark = pytest.mark.integration


@pytest.fixture
def products(gym_context: ApplicationContext) -> ProductService:
    return gym_context.container.resolve(ProductService)


@pytest.fixture
def pos(gym_context: ApplicationContext) -> PosService:
    return gym_context.container.resolve(PosService)


def _product_id(context: ApplicationContext, sku: str) -> int:
    with context.new_unit_of_work() as uow:
        return ProductRepository(uow.session).find_by_sku(sku).id


def _product_stock(context: ApplicationContext, sku: str) -> int:
    with context.new_unit_of_work() as uow:
        return ProductRepository(uow.session).find_by_sku(sku).stock_quantity


def test_sample_products_are_seeded(products):
    listing = products.list_products()
    assert listing.is_success
    skus = {p.sku for p in listing.value.items}
    assert {"WATER", "PROTEIN-BAR", "WHEY-SCOOP"} <= skus


def test_create_product(products):
    result = products.create_product(
        CreateProductRequest(name="Shaker", price=Decimal("75.00"), stock_quantity=20)
    )
    assert result.is_success
    assert result.value.sku.startswith("P")


def test_checkout_decrements_stock_and_records_revenue(gym_context, pos):
    water_id = _product_id(gym_context, "WATER")  # price 10.00, stock 100
    payments = gym_context.container.resolve(PaymentService)

    result = pos.checkout([CartLine(product_id=water_id, quantity=3)])
    assert result.is_success
    assert result.value.total == Decimal("30.00")
    assert result.value.item_count == 3

    assert _product_stock(gym_context, "WATER") == 97
    assert payments.total_revenue() == Decimal("30.00")  # POS payment auto-recorded


def test_checkout_insufficient_stock(gym_context, pos):
    whey_id = _product_id(gym_context, "WHEY-SCOOP")  # stock 40
    result = pos.checkout([CartLine(product_id=whey_id, quantity=9999)])
    assert result.is_failure
    assert result.error.code is ErrorCode.BUSINESS_RULE


def test_checkout_empty_cart(pos):
    result = pos.checkout([])
    assert result.is_failure
    assert result.error.code is ErrorCode.BUSINESS_RULE
