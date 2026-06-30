from decimal import Decimal

import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.expenses.dtos import RecordExpenseRequest
from app.modules.expenses.services import ExpenseService

pytestmark = pytest.mark.integration


@pytest.fixture
def expenses(gym_context: ApplicationContext) -> ExpenseService:
    return gym_context.container.resolve(ExpenseService)


def test_record_expense_updates_totals(expenses):
    assert expenses.record_expense(
        RecordExpenseRequest(category="Rent", amount=Decimal("500.00"))
    ).is_success
    assert expenses.total_expenses() == Decimal("500.00")
    assert expenses.today_expenses() == Decimal("500.00")


def test_record_expense_requires_category(expenses):
    result = expenses.record_expense(RecordExpenseRequest(category="  ", amount=Decimal("10")))
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_list_expenses(expenses):
    expenses.record_expense(RecordExpenseRequest(category="Power", amount=Decimal("80")))
    expenses.record_expense(RecordExpenseRequest(category="Water", amount=Decimal("20")))
    result = expenses.list_expenses()
    assert result.is_success
    assert result.value.total == 2
