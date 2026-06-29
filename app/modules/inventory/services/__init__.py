"""Inventory module services."""

from app.modules.inventory.services.pos_service import PosService
from app.modules.inventory.services.product_service import ProductService

__all__ = ["PosService", "ProductService"]
