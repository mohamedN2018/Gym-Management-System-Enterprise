"""Abstract building blocks every module specializes.

These are persistence- and UI-agnostic contracts (the *Domain* layer's seams):

- :class:`~app.core.base.dto.BaseDTO`               — Pydantic v2 DTO base
- :class:`~app.core.base.repository.IRepository`    — repository interface
- :class:`~app.core.base.unit_of_work.IUnitOfWork`  — transactional boundary
- :class:`~app.core.base.service.BaseService`       — service base (Result + events + logging)
- :class:`~app.core.base.validator.BaseValidator`   — validator base + :class:`ValidationResult`
"""

from app.core.base.dto import BaseDTO
from app.core.base.repository import IRepository
from app.core.base.service import BaseService
from app.core.base.unit_of_work import IUnitOfWork
from app.core.base.validator import BaseValidator, ValidationResult

__all__ = [
    "BaseDTO",
    "BaseService",
    "BaseValidator",
    "IRepository",
    "IUnitOfWork",
    "ValidationResult",
]
