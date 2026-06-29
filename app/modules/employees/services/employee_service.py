"""Employee management service."""

from __future__ import annotations

from collections.abc import Callable

from app.core.base.service import BaseService
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest, Sort
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.employees.dtos import CreateEmployeeRequest, EmployeeDTO, to_employee_dto
from app.modules.employees.events import EmployeeEvents
from app.modules.employees.models.employee import Employee
from app.modules.employees.repositories import EmployeeRepository
from app.modules.employees.validators import CreateEmployeeValidator

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


class EmployeeService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._validator = CreateEmployeeValidator()

    def create_employee(
        self, request: CreateEmployeeRequest, *, created_by: int | None = None
    ) -> Result[EmployeeDTO]:
        def _create() -> EmployeeDTO:
            self._validator.validate_and_raise(request)
            with self._uow_factory() as uow:
                repo = EmployeeRepository(uow.session)
                code = (
                    request.code or ""
                ).strip() or f"E{repo.count(include_deleted=True) + 1:04d}"
                employee = Employee(
                    code=code,
                    first_name=request.first_name.strip(),
                    last_name=(request.last_name or None),
                    phone=(request.phone or None),
                    position=(request.position or None),
                    department=(request.department or None),
                    salary=request.salary,
                    created_by=created_by,
                )
                repo.add(employee)
                dto = to_employee_dto(employee)
                uow.commit()
            self._publish(Event(EmployeeEvents.CREATED, {"employee_id": dto.id, "code": dto.code}))
            return dto

        return self._guard(_create, message="Could not create employee")

    def list_employees(self, request: PageRequest | None = None) -> Result[Page[EmployeeDTO]]:
        def _list() -> Page[EmployeeDTO]:
            with self._uow_factory() as uow:
                page = EmployeeRepository(uow.session).list(
                    request or PageRequest(sort=(Sort.asc("code"),))
                )
                return Page(
                    items=[to_employee_dto(e) for e in page.items],
                    total=page.total,
                    page=page.page,
                    size=page.size,
                )

        return self._guard(_list, message="Could not list employees")
