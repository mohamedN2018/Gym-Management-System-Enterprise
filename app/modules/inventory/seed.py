"""Idempotent seeding of a few sample products (so the POS is usable out of the box)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.modules.inventory.models.product import Product
from app.modules.inventory.repositories import ProductRepository

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


@dataclass(frozen=True, slots=True)
class _ProductSeed:
    sku: str
    name: str
    price: Decimal
    stock: int
    category: str


_DEFAULTS: tuple[_ProductSeed, ...] = (
    _ProductSeed("WATER", "Water bottle", Decimal("10.00"), 100, "drinks"),
    _ProductSeed("PROTEIN-BAR", "Protein bar", Decimal("35.00"), 60, "supplements"),
    _ProductSeed("WHEY-SCOOP", "Whey scoop", Decimal("50.00"), 40, "supplements"),
)


def seed_sample_products(uow_factory: UnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        repo = ProductRepository(uow.session)
        for spec in _DEFAULTS:
            if repo.find_by_sku(spec.sku) is None:
                repo.add(
                    Product(
                        sku=spec.sku,
                        name=spec.name,
                        price=spec.price,
                        stock_quantity=spec.stock,
                        category=spec.category,
                    )
                )
        uow.commit()
