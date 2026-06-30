"""Inventory DTOs + mappers."""

from __future__ import annotations

from decimal import Decimal

from app.core.base.dto import BaseDTO
from app.modules.inventory.models.product import Product


class CreateProductRequest(BaseDTO):
    name: str
    price: Decimal = Decimal("0")
    stock_quantity: int = 0
    category: str | None = None
    barcode: str | None = None
    sku: str | None = None


class UpdateProductRequest(BaseDTO):
    """Editable product fields. The SKU is immutable (auto-generated, used for lookups)."""

    name: str
    price: Decimal = Decimal("0")
    stock_quantity: int = 0
    category: str | None = None
    barcode: str | None = None


class ProductDTO(BaseDTO):
    id: int
    sku: str
    name: str
    price: Decimal
    stock_quantity: int
    category: str | None = None
    barcode: str | None = None


class CartLine(BaseDTO):
    product_id: int
    quantity: int = 1


class SaleDTO(BaseDTO):
    id: int
    total: Decimal
    item_count: int


def to_product_dto(product: Product) -> ProductDTO:
    return ProductDTO(
        id=product.id,
        sku=product.sku,
        name=product.name,
        price=product.price,
        stock_quantity=product.stock_quantity,
        category=product.category,
        barcode=product.barcode,
    )
