"""Inventory repositories (persistence only)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.inventory.models.product import Product
from app.modules.inventory.models.sale import Sale


class ProductRepository(SqlAlchemyRepository[Product]):
    searchable_fields = ("sku", "name", "barcode", "category")

    def __init__(self, session: Session) -> None:
        super().__init__(Product, session)

    def find_by_sku(self, sku: str) -> Product | None:
        return self.find_one(sku=sku)

    def low_stock(self, threshold: int) -> list[Product]:
        """Products at or below ``threshold`` units, lowest first."""
        stmt = (
            select(Product)
            .where(Product.is_deleted.is_(False), Product.stock_quantity <= threshold)
            .order_by(Product.stock_quantity.asc())
        )
        return list(self._session.execute(stmt).scalars().all())


class SaleRepository(SqlAlchemyRepository[Sale]):
    def __init__(self, session: Session) -> None:
        super().__init__(Sale, session)
