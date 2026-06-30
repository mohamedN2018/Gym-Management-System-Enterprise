from decimal import Decimal

import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.expenses.dtos import RecordExpenseRequest, UpdateExpenseRequest
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


def test_update_expense_changes_fields_and_keeps_paid_at(expenses):
    created = expenses.record_expense(
        RecordExpenseRequest(category="Rent", amount=Decimal("500.00"), note="old")
    )
    assert created.is_success
    expense_id = created.value.id
    original_paid_at = created.value.paid_at

    result = expenses.update_expense(
        expense_id,
        UpdateExpenseRequest(category="Rent ", amount=Decimal("650.00"), note="new"),
    )
    assert result.is_success
    assert result.value.category == "Rent"
    assert result.value.amount == Decimal("650.00")
    assert result.value.note == "new"
    assert result.value.paid_at == original_paid_at
    assert expenses.total_expenses() == Decimal("650.00")


def test_update_expense_requires_category(expenses):
    created = expenses.record_expense(
        RecordExpenseRequest(category="Rent", amount=Decimal("500.00"))
    )
    result = expenses.update_expense(
        created.value.id, UpdateExpenseRequest(category="  ", amount=Decimal("10"))
    )
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_delete_expense_removes_from_totals_and_listing(expenses):
    created = expenses.record_expense(
        RecordExpenseRequest(category="Rent", amount=Decimal("500.00"))
    )
    assert created.is_success

    result = expenses.delete_expense(created.value.id)
    assert result.is_success
    assert expenses.total_expenses() == Decimal("0")
    listing = expenses.list_expenses()
    assert listing.is_success
    assert listing.value.total == 0
