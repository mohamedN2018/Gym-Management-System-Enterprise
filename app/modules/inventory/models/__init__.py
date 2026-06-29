"""Inventory module ORM models."""

from app.modules.inventory.models.product import Product
from app.modules.inventory.models.sale import Sale, SaleItem

__all__ = ["Product", "Sale", "SaleItem"]
