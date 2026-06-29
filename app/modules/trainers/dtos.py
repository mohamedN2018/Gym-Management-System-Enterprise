"""Trainer DTOs + mapper."""

from __future__ import annotations

from app.core.base.dto import BaseDTO
from app.modules.trainers.models.trainer import Trainer


class CreateTrainerRequest(BaseDTO):
    first_name: str
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    specialty: str | None = None
    code: str | None = None


class TrainerDTO(BaseDTO):
    id: int
    code: str
    first_name: str
    last_name: str | None = None
    full_name: str
    phone: str | None = None
    email: str | None = None
    specialty: str | None = None
    is_active: bool = True


def to_trainer_dto(trainer: Trainer) -> TrainerDTO:
    return TrainerDTO(
        id=trainer.id,
        code=trainer.code,
        first_name=trainer.first_name,
        last_name=trainer.last_name,
        full_name=trainer.full_name,
        phone=trainer.phone,
        email=trainer.email,
        specialty=trainer.specialty,
        is_active=trainer.is_active,
    )
