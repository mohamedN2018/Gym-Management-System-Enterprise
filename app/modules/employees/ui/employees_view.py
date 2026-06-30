"""Employees view — list + add/edit/delete (presentation only)."""

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
from app.modules.employees.dtos import (
    CreateEmployeeRequest,
    EmployeeDTO,
    UpdateEmployeeRequest,
)
from app.modules.employees.services import EmployeeService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "employees.col_code",
    "employees.col_name",
    "employees.col_phone",
    "employees.col_position",
    "employees.col_department",
    "employees.col_salary",
)


class _EmployeeFormDialog(QDialog):
    def __init__(
        self,
        localization: LocalizationService,
        parent: QWidget | None = None,
        *,
        employee: EmployeeDTO | None = None,
    ) -> None:
        super().__init__(parent)
        self._loc = localization
        self._employee = employee
        self.setModal(True)
        self.setMinimumWidth(400)
        tr = localization.tr
        self.setWindowTitle(
            tr("employee_form.title") if employee is None else tr("employee_form.edit_title")
        )

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._first = QLineEdit()
        self._last = QLineEdit()
        self._phone = QLineEdit()
        self._position = QLineEdit()
        self._department = QLineEdit()
        self._salary = QLineEdit("0")
        form.addRow(tr("employee_form.first_name"), self._first)
        form.addRow(tr("employee_form.last_name"), self._last)
        form.addRow(tr("employee_form.phone"), self._phone)
        form.addRow(tr("employee_form.position"), self._position)
        form.addRow(tr("employee_form.department"), self._department)
        form.addRow(tr("employee_form.salary"), self._salary)
        root.addLayout(form)

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

        if employee is not None:
            self._prefill(employee)

    def _prefill(self, employee: EmployeeDTO) -> None:
        self._first.setText(employee.first_name)
        self._last.setText(employee.last_name or "")
        self._phone.setText(employee.phone or "")
        self._position.setText(employee.position or "")
        self._department.setText(employee.department or "")
        self._salary.setText(f"{employee.salary:.2f}" if employee.salary is not None else "0")

    def _on_accept(self) -> None:
        if not self._first.text().strip():
            return self._fail("employee_form.first_name_required")
        try:
            self._parsed_salary = Decimal(self._salary.text().strip() or "0")
        except (InvalidOperation, ValueError):
            return self._fail("employee_form.invalid_salary")
        if self._parsed_salary < 0:
            return self._fail("employee_form.invalid_salary")
        self.accept()
        return None

    def _fail(self, key: str) -> None:
        self._error.setText(self._loc.tr(key))
        self._error.setVisible(True)

    @staticmethod
    def _value(field: QLineEdit) -> str | None:
        return field.text().strip() or None

    def to_request(self) -> CreateEmployeeRequest:
        return CreateEmployeeRequest(
            first_name=self._first.text().strip(),
            last_name=self._value(self._last),
            phone=self._value(self._phone),
            position=self._value(self._position),
            department=self._value(self._department),
            salary=self._parsed_salary,
        )

    def to_update_request(self) -> UpdateEmployeeRequest:
        return UpdateEmployeeRequest(
            first_name=self._first.text().strip(),
            last_name=self._value(self._last),
            phone=self._value(self._phone),
            position=self._value(self._position),
            department=self._value(self._department),
            salary=self._parsed_salary,
        )


class EmployeesView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._current_user = current_user
        self._service: EmployeeService = context.container.resolve(EmployeeService)
        self._employees_data: list[EmployeeDTO] = []
        self._build_ui()
        self._unsubscribe = self._loc.on_change(lambda _c: self._retranslate())
        self.destroyed.connect(lambda: self._unsubscribe())
        self._retranslate()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)

        bar = QHBoxLayout()
        bar.addStretch(1)
        self._edit = QPushButton()
        self._edit.clicked.connect(self._on_edit)
        bar.addWidget(self._edit)
        self._delete = QPushButton()
        self._delete.setObjectName("DangerButton")
        self._delete.clicked.connect(self._on_delete)
        bar.addWidget(self._delete)
        self._add = QPushButton()
        self._add.setObjectName("PrimaryButton")
        self._add.clicked.connect(self._on_add)
        bar.addWidget(self._add)
        layout.addLayout(bar)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.doubleClicked.connect(lambda _i: self._on_edit())
        layout.addWidget(self._table, 1)

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("employees.title"))
        self._add.setText(tr("employees.add"))
        self._edit.setText(tr("employees.edit"))
        self._delete.setText(tr("employees.delete"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])

    def reload(self) -> None:
        result = self._service.list_employees(PageRequest(size=300, sort=(Sort.asc("code"),)))
        if result.is_failure:
            return
        self._populate(result.value.items)

    def _populate(self, employees: list[EmployeeDTO]) -> None:
        self._employees_data = employees
        self._table.setRowCount(len(employees))
        for row, employee in enumerate(employees):
            values = (
                employee.code,
                employee.full_name,
                employee.phone or "—",
                employee.position or "—",
                employee.department or "—",
                f"{employee.salary:.2f}" if employee.salary is not None else "—",
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))

    def _on_add(self) -> None:
        dialog = _EmployeeFormDialog(self._loc, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._service.create_employee(dialog.to_request(), created_by=created_by)
        if result.is_failure:
            self._show_error(result.error.message if result.error else "")
            return
        self.reload()

    def _on_edit(self) -> None:
        employee = self._selected_employee()
        if employee is None:
            self._require_selection()
            return
        dialog = _EmployeeFormDialog(self._loc, self, employee=employee)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated_by = self._current_user.id if self._current_user is not None else None
        result = self._service.update_employee(
            employee.id, dialog.to_update_request(), updated_by=updated_by
        )
        if result.is_failure:
            self._show_error(result.error.message if result.error else "")
            return
        self.reload()

    def _on_delete(self) -> None:
        employee = self._selected_employee()
        if employee is None:
            self._require_selection()
            return
        confirm = QMessageBox.question(
            self,
            self._loc.tr("employees.delete_title"),
            self._loc.tr("employees.delete_confirm", name=employee.full_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        deleted_by = self._current_user.id if self._current_user is not None else None
        result = self._service.delete_employee(employee.id, deleted_by=deleted_by)
        if result.is_failure:
            self._show_error(result.error.message if result.error else "")
            return
        self.reload()

    def _require_selection(self) -> None:
        QMessageBox.information(
            self, self._loc.tr("employees.title"), self._loc.tr("employees.select_first")
        )

    def _selected_employee(self) -> EmployeeDTO | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._employees_data):
            return None
        return self._employees_data[row]

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, self._loc.tr("employees.title"), message)
