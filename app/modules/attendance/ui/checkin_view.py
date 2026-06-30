"""Check-in view — enter/scan a membership number, see allow/reject + today's log."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.bootstrap import ApplicationContext
from app.modules.attendance.dtos import CheckInResult
from app.modules.attendance.services import AttendanceService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "checkin.col_time",
    "checkin.col_number",
    "checkin.col_member",
    "checkin.col_status",
)


class CheckInView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._service: AttendanceService = context.container.resolve(AttendanceService)
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

        entry = QHBoxLayout()
        entry.setSpacing(10)
        self._input = QLineEdit()
        self._input.setMinimumHeight(40)
        self._input.returnPressed.connect(self._on_check_in)
        entry.addWidget(self._input, 1)
        self._button = QPushButton()
        self._button.setMinimumHeight(40)
        self._button.clicked.connect(self._on_check_in)
        entry.addWidget(self._button, 0)
        layout.addLayout(entry)

        self._banner = QLabel()
        self._banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._banner.setMinimumHeight(48)
        self._banner.setVisible(False)
        layout.addWidget(self._banner)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("checkin.title"))
        self._input.setPlaceholderText(tr("checkin.placeholder"))
        self._button.setText(tr("checkin.button"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])

    def _on_check_in(self) -> None:
        number = self._input.text().strip()
        if not number:
            return
        result = self._service.check_in(number)
        if result.is_success:
            self._show_result(result.value)
        self._input.clear()
        self._input.setFocus()
        self.reload()

    def _show_result(self, result: CheckInResult) -> None:
        tr = self._loc.tr
        if result.allowed:
            text = tr(
                "checkin.allowed_message",
                name=result.member_name or "",
                days=result.remaining_days if result.remaining_days is not None else 0,
            )
        elif result.reason == "not_found":
            text = tr("checkin.reason_not_found")
        else:
            text = tr("checkin.reason_no_sub")
        self._banner.setText(text)
        self._banner.setObjectName("StatusOk" if result.allowed else "StatusBad")
        self._banner.style().unpolish(self._banner)
        self._banner.style().polish(self._banner)
        self._banner.setVisible(True)

    def reload(self) -> None:
        result = self._service.list_today()
        if result.is_failure:
            return
        rows = result.value
        self._table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            status = self._loc.tr("checkin.allowed" if row.allowed else "checkin.rejected")
            values = (
                row.checked_in_at.strftime("%H:%M:%S"),
                row.membership_number,
                row.member_name,
                status,
            )
            for column, value in enumerate(values):
                self._table.setItem(index, column, QTableWidgetItem(value))
