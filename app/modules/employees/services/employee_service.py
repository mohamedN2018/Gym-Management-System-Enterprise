"""Employee management service."""

from __future__ import annotations

from collections.abc import Callable

from app.core.base.service import BaseService
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest, Sort
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.employees.dtos import (
    CreateEmployeeRequest,
    EmployeeDTO,
    UpdateEmployeeRequest,
    to_employee_dto,
)
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
        self._logging = logging
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
            if self._logging:
                self._logging.audit(
                    action="create",
                    module="employees",
                    result="success",
                    user=created_by,
                    new_value={"code": dto.code, "id": dto.id},
                )
            self._publish(Event(EmployeeEvents.CREATED, {"employee_id": dto.id, "code": dto.code}))
            return dto

        return self._guard(_create, message="Could not create employee")

    def update_employee(
        self, employee_id: int, request: UpdateEmployeeRequest, *, updated_by: int | None = None
    ) -> Result[EmployeeDTO]:
        return self._guard(
            lambda: self._update_employee(employee_id, request, updated_by),
            message="Could not update employee",
        )

    def _update_employee(
        self, employee_id: int, request: UpdateEmployeeRequest, updated_by: int | None
    ) -> EmployeeDTO:
        self._validator.validate_and_raise(request)
        with self._uow_factory() as uow:
            repo = EmployeeRepository(uow.session)
            employee = repo.get_or_raise(employee_id)
            employee.first_name = request.first_name.strip()
            employee.last_name = (request.last_name or "").strip() or None
            employee.phone = (request.phone or "").strip() or None
            employee.position = (request.position or "").strip() or None
            employee.department = (request.department or "").strip() or None
            employee.salary = request.salary
            employee.updated_by = updated_by
            repo.update(employee)
            dto = to_employee_dto(employee)
            uow.commit()
        if self._logging:
            self._logging.audit(
                action="update",
                module="employees",
                result="success",
                user=updated_by,
                new_value={"code": dto.code, "id": dto.id},
            )
        self._publish(Event(EmployeeEvents.UPDATED, {"employee_id": dto.id, "code": dto.code}))
        return dto

    def delete_employee(self, employee_id: int, *, deleted_by: int | None = None) -> Result[None]:
        def _delete() -> None:
            with self._uow_factory() as uow:
                repo = EmployeeRepository(uow.session)
                employee = repo.get_or_raise(employee_id)
                repo.soft_delete(employee, by=deleted_by)
                uow.commit()
            if self._logging:
                self._logging.audit(
                    action="delete",
                    module="employees",
                    result="success",
                    user=deleted_by,
                    new_value={"id": employee_id},
                )
            self._publish(Event(EmployeeEvents.DELETED, {"employee_id": employee_id}))

        return self._guard(_delete, message="Could not delete employee")

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
