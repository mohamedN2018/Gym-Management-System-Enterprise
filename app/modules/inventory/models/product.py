"""Product entity — a sellable inventory item (supplement, drink, accessory)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Entity


class Product(Entity):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    stock_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
