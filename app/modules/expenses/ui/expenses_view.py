"""Expenses view — list expenses + add, with a totals summary (presentation only)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.pagination import PageRequest, Sort
from app.infrastructure.bootstrap import ApplicationContext
from app.localization.localization_service import LocalizationService
from app.modules.expenses.dtos import ExpenseDTO, RecordExpenseRequest, UpdateExpenseRequest
from app.modules.expenses.services import ExpenseService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "expenses.col_date",
    "expenses.col_category",
    "expenses.col_amount",
    "expenses.col_note",
)


class _ExpenseFormDialog(QDialog):
    def __init__(
        self,
        localization: LocalizationService,
        parent: QWidget | None = None,
        *,
        expense: ExpenseDTO | None = None,
    ) -> None:
        super().__init__(parent)
        self._loc = localization
        self._expense = expense
        self.setModal(True)
        self.setMinimumWidth(380)
        tr = localization.tr
        self.setWindowTitle(
            tr("expense_form.title") if expense is None else tr("expense_form.edit_title")
        )

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._category = QLineEdit()
        self._amount = QLineEdit("0")
        self._note = QLineEdit()
        form.addRow(tr("expense_form.category"), self._category)
        form.addRow(tr("expense_form.amount"), self._amount)
        form.addRow(tr("expense_form.note"), self._note)
        root.addLayout(form)

        if expense is not None:
            self._prefill(expense)

        self._error = QLabel()
        self._error.setObjectName("StatusBad")
        self._error.setVisible(False)
        root.addWidget(self._error)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(tr("common.cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(tr("common.save"))
        save.setDefault(True)
        save.clicked.connect(self._on_accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def _on_accept(self) -> None:
        if not self._category.text().strip():
            return self._fail("expense_form.category_required")
        try:
            self._parsed_amount = Decimal(self._amount.text().strip() or "0")
        except InvalidOperation:
            return self._fail("expense_form.invalid_amount")
        if self._parsed_amount < 0:
            return self._fail("expense_form.invalid_amount")
        self.accept()
        return None

    def _fail(self, key: str) -> None:
        self._error.setText(self._loc.tr(key))
        self._error.setVisible(True)

    def _prefill(self, expense: ExpenseDTO) -> None:
        self._category.setText(expense.category)
        self._amount.setText(f"{expense.amount:.2f}")
        self._note.setText(expense.note or "")

    def to_request(self) -> RecordExpenseRequest:
        return RecordExpenseRequest(
            category=self._category.text().strip(),
            amount=self._parsed_amount,
            note=self._note.text().strip() or None,
        )

    def to_update_request(self) -> UpdateExpenseRequest:
        return UpdateExpenseRequest(
            category=self._category.text().strip(),
            amount=self._parsed_amount,
            note=self._note.text().strip() or None,
        )


class ExpensesView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._current_user = current_user
        self._service: ExpenseService = context.container.resolve(ExpenseService)
        self._expenses_data: list[ExpenseDTO] = []
        self._build_ui()
        self._unsubscribe = self._loc.on_change(lambda _c: self._retranslate())
        self.destroyed.connect(lambda: self._unsubscribe())
        self._retranslate()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)

        bar = QHBoxLayout()
        self._summary = QLabel()
        self._summary.setObjectName("CardValue")
        bar.addWidget(self._summary, 1)
        self._edit = QPushButton()
        self._edit.clicked.connect(self._on_edit)
        bar.addWidget(self._edit)
        self._delete = QPushButton()
        self._delete.setObjectName("DangerButton")
        self._delete.clicked.connect(self._on_delete)
        bar.addWidget(self._delete)
        self._add = QPushButton()
        self._add.clicked.connect(self._on_add)
        bar.addWidget(self._add)
        layout.addLayout(bar)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("expenses.title"))
        self._add.setText(tr("expenses.add"))
        self._edit.setText(tr("expenses.edit"))
        self._delete.setText(tr("expenses.delete"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])
        self._update_summary()

    def _update_summary(self) -> None:
        tr = self._loc.tr
        total = self._service.total_expenses()
        today = self._service.today_expenses()
        self._summary.setText(
            f"{tr('expenses.total')}: {total:.2f}   •   {tr('expenses.today')}: {today:.2f}"
        )

    def reload(self) -> None:
        result = self._service.list_expenses(PageRequest(size=300, sort=(Sort.desc("paid_at"),)))
        if result.is_failure:
            return
        self._populate(result.value.items)
        self._update_summary()

    def _populate(self, expenses: list[ExpenseDTO]) -> None:
        self._expenses_data = expenses
        self._table.setRowCount(len(expenses))
        for row, expense in enumerate(expenses):
            values = (
                expense.paid_at.strftime("%Y-%m-%d %H:%M"),
                expense.category,
                f"{expense.amount:.2f}",
                expense.note or "",
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))

    def _on_add(self) -> None:
        dialog = _ExpenseFormDialog(self._loc, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._service.record_expense(dialog.to_request(), created_by=created_by)
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("expenses.title"), result.error.message if result.error else ""
            )
            return
        self.reload()

    def _on_edit(self) -> None:
        expense = self._selected_expense()
        if expense is None:
            self._require_selection()
            return
        dialog = _ExpenseFormDialog(self._loc, self, expense=expense)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated_by = self._current_user.id if self._current_user is not None else None
        result = self._service.update_expense(
            expense.id, dialog.to_update_request(), updated_by=updated_by
        )
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("expenses.title"), result.error.message if result.error else ""
            )
            return
        self.reload()

    def _on_delete(self) -> None:
        expense = self._selected_expense()
        if expense is None:
            self._require_selection()
            return
        confirm = QMessageBox.question(
            self,
            self._loc.tr("expenses.delete_title"),
            self._loc.tr("expenses.delete_confirm", name=expense.category),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        deleted_by = self._current_user.id if self._current_user is not None else None
        result = self._service.delete_expense(expense.id, deleted_by=deleted_by)
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("expenses.title"), result.error.message if result.error else ""
            )
            return
        self.reload()

    def _require_selection(self) -> None:
        QMessageBox.information(
            self, self._loc.tr("expenses.title"), self._loc.tr("expenses.select_first")
        )

    def _selected_expense(self) -> ExpenseDTO | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._expenses_data):
            return None
        return self._expenses_data[row]
