"""Measurement service — record and list a member's body measurements (weight/height/BMI)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from app.core.base.service import BaseService
from app.core.errors import NotFoundError, ValidationError
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.members.dtos import CreateMeasurementRequest, MeasurementDTO, to_measurement_dto
from app.modules.members.models.measurement import MemberMeasurement
from app.modules.members.repositories import MeasurementRepository, MemberRepository

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]
NowProvider = Callable[[], datetime]


class MeasurementService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        now_provider: NowProvider,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None)
        self._uow_factory = uow_factory
        self._now = now_provider

    def record_measurement(
        self, request: CreateMeasurementRequest, *, created_by: int | None = None
    ) -> Result[MeasurementDTO]:
        def _record() -> MeasurementDTO:
            if (request.weight_kg is None or request.weight_kg <= 0) and (
                request.height_cm is None or request.height_cm <= 0
            ):
                raise ValidationError(
                    "Enter a weight and/or a height.",
                    details={"fields": {"weight_kg": ["required"]}},
                )
            if request.weight_kg is not None and request.weight_kg < 0:
                raise ValidationError("Weight must be positive.")
            if request.height_cm is not None and request.height_cm < 0:
                raise ValidationError("Height must be positive.")
            with self._uow_factory() as uow:
                if MemberRepository(uow.session).get(request.member_id) is None:
                    raise NotFoundError(
                        "Member not found.", details={"member_id": request.member_id}
                    )
                measurement = MemberMeasurement(
                    member_id=request.member_id,
                    weight_kg=request.weight_kg,
                    height_cm=request.height_cm,
                    measured_at=self._now(),
                    created_by=created_by,
                )
                MeasurementRepository(uow.session).add(measurement)
                dto = to_measurement_dto(measurement)
                uow.commit()
            return dto

        return self._guard(_record, message="Could not record measurement")

    def list_measurements(self, member_id: int) -> Result[list[MeasurementDTO]]:
        def _list() -> list[MeasurementDTO]:
            with self._uow_factory() as uow:
                rows = MeasurementRepository(uow.session).for_member(member_id)
                return [to_measurement_dto(row) for row in rows]

        return self._guard(_list, message="Could not list measurements")

    def latest(self, member_id: int) -> Result[MeasurementDTO | None]:
        def _latest() -> MeasurementDTO | None:
            with self._uow_factory() as uow:
                rows = MeasurementRepository(uow.session).for_member(member_id)
                return to_measurement_dto(rows[0]) if rows else None

        return self._guard(_latest, message="Could not load measurement")

    @staticmethod
    def bmi_of(weight_kg: Decimal | None, height_cm: Decimal | None) -> Decimal | None:
        if not weight_kg or not height_cm or height_cm == 0:
            return None
        height_m = height_cm / Decimal("100")
        return (weight_kg / (height_m * height_m)).quantize(Decimal("0.01"))
