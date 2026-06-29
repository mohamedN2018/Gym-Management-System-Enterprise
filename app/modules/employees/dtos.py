"""Employee DTOs + mapper."""

from __future__ import annotations

from decimal import Decimal

from app.core.base.dto import BaseDTO
from app.modules.employees.models.employee import Employee


class CreateEmployeeRequest(BaseDTO):
    first_name: str
    last_name: str | None = None
    phone: str | None = None
    position: str | None = None
    department: str | None = None
    salary: Decimal | None = None
    code: str | None = None


class EmployeeDTO(BaseDTO):
    id: int
    code: str
    first_name: str
    last_name: str | None = None
    full_name: str
    phone: str | None = None
    position: str | None = None
    department: str | None = None
    salary: Decimal | None = None


def to_employee_dto(employee: Employee) -> EmployeeDTO:
    return EmployeeDTO(
        id=employee.id,
        code=employee.code,
        first_name=employee.first_name,
        last_name=employee.last_name,
        full_name=employee.full_name,
        phone=employee.phone,
        position=employee.position,
        department=employee.department,
        salary=employee.salary,
    )
