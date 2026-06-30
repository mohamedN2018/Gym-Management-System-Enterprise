from decimal import Decimal

import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.inventory.dtos import CartLine, CreateProductRequest, UpdateProductRequest
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


def test_create_product_persists_barcode(products):
    result = products.create_product(
        CreateProductRequest(name="Towel", price=Decimal("30.00"), barcode="6291000000001")
    )
    assert result.is_success
    assert result.value.barcode == "6291000000001"


def test_update_product_edits_fields_and_keeps_sku(products):
    created = products.create_product(
        CreateProductRequest(name="Strap", price=Decimal("20.00"), stock_quantity=5)
    )
    assert created.is_success
    sku = created.value.sku

    updated = products.update_product(
        created.value.id,
        UpdateProductRequest(
            name="Lifting Strap",
            price=Decimal("25.50"),
            stock_quantity=12,
            category="Accessories",
            barcode="6291000000002",
        ),
    )
    assert updated.is_success
    assert updated.value.sku == sku  # SKU immutable
    assert updated.value.name == "Lifting Strap"
    assert updated.value.price == Decimal("25.50")
    assert updated.value.stock_quantity == 12
    assert updated.value.category == "Accessories"
    assert updated.value.barcode == "6291000000002"


def test_update_product_not_found(products):
    result = products.update_product(
        999999, UpdateProductRequest(name="Ghost", price=Decimal("1.00"))
    )
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_delete_product_soft_deletes(products):
    created = products.create_product(
        CreateProductRequest(name="Disposable", price=Decimal("5.00"))
    )
    assert created.is_success

    deleted = products.delete_product(created.value.id)
    assert deleted.is_success

    listing = products.list_products()
    assert listing.is_success
    assert created.value.id not in {p.id for p in listing.value.items}


def test_delete_product_not_found(products):
    result = products.delete_product(999999)
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


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
