"""Payments view — read-only list of payments with a revenue summary (presentation only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.pagination import PageRequest, Sort
from app.infrastructure.bootstrap import ApplicationContext
from app.modules.payments.dtos import PaymentDTO
from app.modules.payments.services import PaymentService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "payments.col_date",
    "payments.col_member",
    "payments.col_type",
    "payments.col_method",
    "payments.col_amount",
    "payments.col_reference",
    "payments.col_note",
)


class PaymentsView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._service: PaymentService = context.container.resolve(PaymentService)
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
        self._summary = QLabel()
        self._summary.setObjectName("CardValue")
        layout.addWidget(self._summary)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("payments.title"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])
        self._update_summary()

    def _update_summary(self) -> None:
        tr = self._loc.tr
        total = self._service.total_revenue()
        today = self._service.today_revenue()
        total_text = f"{tr('payments.total_revenue')}: {total:.2f}"
        today_text = f"{tr('payments.today_revenue')}: {today:.2f}"
        self._summary.setText(f"{total_text}   •   {today_text}")

    def reload(self) -> None:
        result = self._service.list_payments(PageRequest(size=200, sort=(Sort.desc("paid_at"),)))
        if result.is_failure:
            return
        self._populate(result.value.items)
        self._update_summary()

    def _populate(self, payments: list[PaymentDTO]) -> None:
        tr = self._loc.tr
        self._table.setRowCount(len(payments))
        for row, payment in enumerate(payments):
            values = (
                payment.paid_at.strftime("%Y-%m-%d %H:%M"),
                payment.member_label or "—",
                tr(f"payment_type.{payment.payment_type}"),
                tr(f"payment_method.{payment.method}"),
                f"{payment.amount:.2f}",
                payment.reference or "—",
                payment.note or "—",
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))
