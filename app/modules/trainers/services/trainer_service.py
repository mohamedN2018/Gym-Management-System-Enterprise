"""Trainer management service."""

from __future__ import annotations

from collections.abc import Callable

from app.core.base.service import BaseService
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.trainers.dtos import (
    CreateTrainerRequest,
    TrainerDTO,
    UpdateTrainerRequest,
    to_trainer_dto,
)
from app.modules.trainers.events import TrainerEvents
from app.modules.trainers.models.trainer import Trainer
from app.modules.trainers.repositories import TrainerRepository
from app.modules.trainers.validators import CreateTrainerValidator

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


class TrainerService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._validator = CreateTrainerValidator()

    def create_trainer(
        self, request: CreateTrainerRequest, *, created_by: int | None = None
    ) -> Result[TrainerDTO]:
        def _create() -> TrainerDTO:
            self._validator.validate_and_raise(request)
            with self._uow_factory() as uow:
                repo = TrainerRepository(uow.session)
                code = (
                    request.code or ""
                ).strip() or f"T{repo.count(include_deleted=True) + 1:04d}"
                trainer = Trainer(
                    code=code,
                    first_name=request.first_name.strip(),
                    last_name=(request.last_name or None),
                    phone=(request.phone or None),
                    email=(request.email or None),
                    specialty=(request.specialty or None),
                    created_by=created_by,
                )
                repo.add(trainer)
                dto = to_trainer_dto(trainer)
                uow.commit()
            self._publish(Event(TrainerEvents.CREATED, {"trainer_id": dto.id, "code": dto.code}))
            return dto

        return self._guard(_create, message="Could not create trainer")

    def update_trainer(
        self, trainer_id: int, request: UpdateTrainerRequest, *, updated_by: int | None = None
    ) -> Result[TrainerDTO]:
        def _update() -> TrainerDTO:
            self._validator.validate_and_raise(request)
            with self._uow_factory() as uow:
                repo = TrainerRepository(uow.session)
                trainer = repo.get_or_raise(trainer_id)
                # The trainer code is immutable (printed on schedules/reports).
                trainer.first_name = request.first_name.strip()
                trainer.last_name = (request.last_name or "").strip() or None
                trainer.phone = (request.phone or "").strip() or None
                trainer.email = (request.email or "").strip() or None
                trainer.specialty = (request.specialty or "").strip() or None
                trainer.updated_by = updated_by
                repo.update(trainer)
                dto = to_trainer_dto(trainer)
                uow.commit()
            self._publish(Event(TrainerEvents.UPDATED, {"trainer_id": dto.id, "code": dto.code}))
            return dto

        return self._guard(_update, message="Could not update trainer")

    def delete_trainer(self, trainer_id: int, *, deleted_by: int | None = None) -> Result[None]:
        def _delete() -> None:
            with self._uow_factory() as uow:
                repo = TrainerRepository(uow.session)
                trainer = repo.get_or_raise(trainer_id)
                repo.soft_delete(trainer, by=deleted_by)
                uow.commit()
            self._publish(Event(TrainerEvents.DELETED, {"trainer_id": trainer_id}))

        return self._guard(_delete, message="Could not delete trainer")

    def list_trainers(self, request: PageRequest | None = None) -> Result[Page[TrainerDTO]]:
        def _list() -> Page[TrainerDTO]:
            with self._uow_factory() as uow:
                page = TrainerRepository(uow.session).list(request or PageRequest())
                return Page(
                    items=[to_trainer_dto(t) for t in page.items],
                    total=page.total,
                    page=page.page,
                    size=page.size,
                )

        return self._guard(_list, message="Could not list trainers")
