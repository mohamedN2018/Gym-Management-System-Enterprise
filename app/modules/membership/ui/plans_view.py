"""Plans view — list membership plans + add (presentation only)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
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
from app.modules.membership.dtos import CreatePlanRequest, PlanDTO, UpdatePlanRequest
from app.modules.membership.services import MembershipService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "plans.col_code",
    "plans.col_name",
    "plans.col_price",
    "plans.col_duration",
    "plans.col_description",
)


class _PlanFormDialog(QDialog):
    def __init__(
        self,
        localization: LocalizationService,
        parent: QWidget | None = None,
        *,
        plan: PlanDTO | None = None,
    ) -> None:
        super().__init__(parent)
        self._loc = localization
        self._plan = plan
        self.setModal(True)
        self.setMinimumWidth(380)
        tr = localization.tr
        self.setWindowTitle(tr("plan_form.edit_title") if plan else tr("plan_form.title"))

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit()
        self._price = QLineEdit("0")
        self._duration = QLineEdit("30")
        self._description = QLineEdit()
        form.addRow(tr("plan_form.name"), self._name)
        form.addRow(tr("plan_form.price"), self._price)
        form.addRow(tr("plan_form.duration"), self._duration)
        form.addRow(tr("plan_form.description"), self._description)
        root.addLayout(form)

        if plan is not None:
            self._prefill(plan)

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

    def _prefill(self, plan: PlanDTO) -> None:
        self._name.setText(plan.name)
        self._price.setText(f"{plan.price:.2f}")
        self._duration.setText(str(plan.duration_days))
        self._description.setText(plan.description or "")

    def _on_accept(self) -> None:
        if not self._name.text().strip():
            return self._fail("plan_form.name_required")
        try:
            self._parsed_price = Decimal(self._price.text().strip() or "0")
            self._parsed_duration = int(self._duration.text().strip() or "0")
        except (InvalidOperation, ValueError):
            return self._fail("plan_form.invalid_numbers")
        if self._parsed_price < 0 or self._parsed_duration < 1:
            return self._fail("plan_form.invalid_numbers")
        self.accept()
        return None

    def _fail(self, key: str) -> None:
        self._error.setText(self._loc.tr(key))
        self._error.setVisible(True)

    def to_request(self) -> CreatePlanRequest:
        return CreatePlanRequest(
            name=self._name.text().strip(),
            price=self._parsed_price,
            duration_days=self._parsed_duration,
            description=self._description.text().strip() or None,
        )

    def to_update_request(self) -> UpdatePlanRequest:
        return UpdatePlanRequest(
            name=self._name.text().strip(),
            price=self._parsed_price,
            duration_days=self._parsed_duration,
            description=self._description.text().strip() or None,
        )


class PlansView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._current_user = current_user
        self._service: MembershipService = context.container.resolve(MembershipService)
        self._plans_data: list[PlanDTO] = []
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
        self._title.setText(tr("plans.title"))
        self._edit.setText(tr("plans.edit"))
        self._delete.setText(tr("plans.delete"))
        self._add.setText(tr("plans.add"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])

    def reload(self) -> None:
        result = self._service.list_plans(PageRequest(size=200, sort=(Sort.asc("duration_days"),)))
        if result.is_failure:
            return
        self._populate(result.value.items)

    def _populate(self, plans: list[PlanDTO]) -> None:
        self._plans_data = plans
        self._table.setRowCount(len(plans))
        for row, plan in enumerate(plans):
            description = (plan.description or "—").splitlines()[0] if plan.description else "—"
            values = (
                plan.code,
                plan.name,
                f"{plan.price:.2f}",
                str(plan.duration_days),
                description,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, column, item)

    def _on_add(self) -> None:
        dialog = _PlanFormDialog(self._loc, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._service.create_plan(dialog.to_request(), created_by=created_by)
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("plans.title"), result.error.message if result.error else ""
            )
            return
        self.reload()

    def _on_edit(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            self._require_selection()
            return
        dialog = _PlanFormDialog(self._loc, self, plan=plan)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated_by = self._current_user.id if self._current_user is not None else None
        result = self._service.update_plan(
            plan.id, dialog.to_update_request(), updated_by=updated_by
        )
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("plans.title"), result.error.message if result.error else ""
            )
            return
        self.reload()

    def _on_delete(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            self._require_selection()
            return
        confirm = QMessageBox.question(
            self,
            self._loc.tr("plans.delete_title"),
            self._loc.tr("plans.delete_confirm", name=plan.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        deleted_by = self._current_user.id if self._current_user is not None else None
        result = self._service.delete_plan(plan.id, deleted_by=deleted_by)
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("plans.title"), result.error.message if result.error else ""
            )
            return
        self.reload()

    def _require_selection(self) -> None:
        QMessageBox.information(
            self, self._loc.tr("plans.title"), self._loc.tr("plans.select_first")
        )

    def _selected_plan(self) -> PlanDTO | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._plans_data):
            return None
        return self._plans_data[row]
