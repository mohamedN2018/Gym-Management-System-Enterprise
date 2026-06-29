"""Subscriptions view — list subscriptions + create (presentation only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
from app.modules.members.services import MemberService
from app.modules.membership.dtos import CreateSubscriptionRequest, PlanDTO, SubscriptionDTO
from app.modules.membership.services import MembershipService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "subscriptions.col_member",
    "subscriptions.col_plan",
    "subscriptions.col_start",
    "subscriptions.col_end",
    "subscriptions.col_status",
)


class _SubscriptionFormDialog(QDialog):
    def __init__(
        self, localization: LocalizationService, plans: list[PlanDTO], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._loc = localization
        self.setModal(True)
        self.setMinimumWidth(400)
        tr = localization.tr
        self.setWindowTitle(tr("subscription_form.title"))

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._member_number = QLineEdit()
        self._member_number.setPlaceholderText(tr("subscription_form.member_number_ph"))
        self._plan = QComboBox()
        for plan in plans:
            self._plan.addItem(f"{plan.name} ({plan.duration_days}d — {plan.price:.2f})", plan.id)
        form.addRow(tr("subscription_form.member_number"), self._member_number)
        form.addRow(tr("subscription_form.plan"), self._plan)
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

    def _on_accept(self) -> None:
        if not self._member_number.text().strip() or self._plan.currentData() is None:
            self._error.setText(self._loc.tr("subscription_form.member_not_found"))
            self._error.setVisible(True)
            return
        self.accept()

    def member_number(self) -> str:
        return self._member_number.text().strip()

    def plan_id(self) -> int:
        return int(self._plan.currentData())

    def show_error(self, key: str) -> None:
        self._error.setText(self._loc.tr(key))
        self._error.setVisible(True)


class SubscriptionsView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._current_user = current_user
        self._service: MembershipService = context.container.resolve(MembershipService)
        self._members: MemberService = context.container.resolve(MemberService)
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
        self._title.setText(tr("subscriptions.title"))
        self._add.setText(tr("subscriptions.add"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])

    def reload(self) -> None:
        result = self._service.list_subscriptions(
            PageRequest(size=200, sort=(Sort.desc("end_date"),))
        )
        if result.is_failure:
            return
        self._populate(result.value.items)

    def _populate(self, subscriptions: list[SubscriptionDTO]) -> None:
        self._table.setRowCount(len(subscriptions))
        for row, sub in enumerate(subscriptions):
            status_label = self._loc.tr(f"subscription_status.{sub.status}")
            values = (
                sub.member_label,
                sub.plan_name,
                sub.start_date.isoformat(),
                sub.end_date.isoformat(),
                status_label,
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))

    def _on_add(self) -> None:
        plans = self._service.list_plans()
        if plans.is_failure or not plans.value.items:
            QMessageBox.warning(
                self, self._loc.tr("subscriptions.title"), self._loc.tr("subscriptions.no_plans")
            )
            return
        dialog = _SubscriptionFormDialog(self._loc, plans.value.items, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        member = self._members.get_by_membership_number(dialog.member_number())
        if member.is_failure or member.value is None:
            QMessageBox.warning(
                self,
                self._loc.tr("subscriptions.title"),
                self._loc.tr("subscription_form.member_not_found"),
            )
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._service.subscribe(
            CreateSubscriptionRequest(member_id=member.value.id, plan_id=dialog.plan_id()),
            created_by=created_by,
        )
        if result.is_failure:
            QMessageBox.warning(
                self,
                self._loc.tr("subscriptions.create_failed"),
                result.error.message if result.error else "",
            )
            return
        self.reload()
