"""Inventory input validators."""

from __future__ import annotations

from app.core.base.validator import BaseValidator, ValidationResult, in_range, max_length, required
from app.modules.inventory.dtos import CreateProductRequest


class CreateProductValidator(BaseValidator[CreateProductRequest]):
    NAME_MAX = 150

    def validate(self, data: CreateProductRequest) -> ValidationResult:
        result = ValidationResult()
        if (msg := required(data.name, "name")) or (
            msg := max_length(data.name, self.NAME_MAX, "name")
        ):
            result.add("name", msg)
        if msg := in_range(float(data.price), 0, None, "price"):
            result.add("price", msg)
        if msg := in_range(data.stock_quantity, 0, None, "stock_quantity"):
            result.add("stock_quantity", msg)
        return result
