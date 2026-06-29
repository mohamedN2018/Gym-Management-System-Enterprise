import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.employees.dtos import CreateEmployeeRequest
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
