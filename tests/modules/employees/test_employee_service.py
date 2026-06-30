from decimal import Decimal

import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.employees.dtos import CreateEmployeeRequest, UpdateEmployeeRequest
from app.modules.employees.services import EmployeeService

pytestmark = pytest.mark.integration


@pytest.fixture
def employees(gym_context: ApplicationContext) -> EmployeeService:
    return gym_context.container.resolve(EmployeeService)


def test_create_employee_autogenerates_code(employees):
    result = employees.create_employee(
        CreateEmployeeRequest(first_name="Layla", position="Coach", department="Training")
    )
    assert result.is_success
    assert result.value.code == "E0001"
    assert result.value.full_name == "Layla"


def test_create_employee_requires_first_name(employees):
    result = employees.create_employee(CreateEmployeeRequest(first_name=""))
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_list_employees(employees):
    employees.create_employee(CreateEmployeeRequest(first_name="A"))
    employees.create_employee(CreateEmployeeRequest(first_name="B"))
    result = employees.list_employees()
    assert result.is_success
    assert result.value.total == 2


def test_create_employee_persists_salary(employees):
    result = employees.create_employee(
        CreateEmployeeRequest(first_name="Omar", salary=Decimal("4500.50"))
    )
    assert result.is_success
    assert result.value.salary == Decimal("4500.50")


def test_update_employee_changes_fields_and_salary(employees):
    created = employees.create_employee(
        CreateEmployeeRequest(first_name="Sara", position="Coach", salary=Decimal("3000"))
    )
    assert created.is_success

    result = employees.update_employee(
        created.value.id,
        UpdateEmployeeRequest(
            first_name="Sara",
            last_name="Ali",
            position="Manager",
            salary=Decimal("5200.75"),
        ),
    )
    assert result.is_success
    assert result.value.code == created.value.code  # code is immutable
    assert result.value.full_name == "Sara Ali"
    assert result.value.position == "Manager"
    assert result.value.salary == Decimal("5200.75")


def test_update_employee_rejects_blank_first_name(employees):
    created = employees.create_employee(CreateEmployeeRequest(first_name="Nadia"))
    assert created.is_success
    result = employees.update_employee(created.value.id, UpdateEmployeeRequest(first_name=""))
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_update_employee_missing_id_fails(employees):
    result = employees.update_employee(99999, UpdateEmployeeRequest(first_name="Ghost"))
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_delete_employee_soft_deletes(employees):
    created = employees.create_employee(CreateEmployeeRequest(first_name="Khaled"))
    assert created.is_success

    result = employees.delete_employee(created.value.id)
    assert result.is_success

    listed = employees.list_employees()
    assert listed.is_success
    assert listed.value.total == 0


def test_delete_employee_missing_id_fails(employees):
    result = employees.delete_employee(99999)
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND
