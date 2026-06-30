"""Inventory module event topics."""

from __future__ import annotations


class InventoryEvents:
    PRODUCT_CREATED = "inventory.product.created"
    PRODUCT_UPDATED = "inventory.product.updated"
    PRODUCT_DELETED = "inventory.product.deleted"
    SALE_COMPLETED = "inventory.sale.completed"
