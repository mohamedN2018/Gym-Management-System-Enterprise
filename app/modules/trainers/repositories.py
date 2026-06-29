"""Trainer repository (persistence only)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.trainers.models.trainer import Trainer


class TrainerRepository(SqlAlchemyRepository[Trainer]):
    searchable_fields = ("code", "first_name", "last_name", "phone", "specialty")

    def __init__(self, session: Session) -> None:
        super().__init__(Trainer, session)
