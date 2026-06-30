"""Audit DTOs."""

from __future__ import annotations

from app.core.base.dto import BaseDTO


class AuditEntryDTO(BaseDTO):
    timestamp: str
    user: str
    module: str
    action: str
    result: str
