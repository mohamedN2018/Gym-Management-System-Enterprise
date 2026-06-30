"""Audit view — read-only table of recent audit-trail entries (presentation only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.bootstrap import ApplicationContext
from app.modules.audit.dtos import AuditEntryDTO
from app.modules.audit.services import AuditService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "audit.col_time",
    "audit.col_user",
    "audit.col_module",
    "audit.col_action",
    "audit.col_result",
)


class AuditView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._service: AuditService = context.container.resolve(AuditService)
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
        bar.addStretch(1)
        self._refresh = QPushButton()
        self._refresh.clicked.connect(self.reload)
        bar.addWidget(self._refresh)
        layout.addLayout(bar)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("audit.title"))
        self._refresh.setText(tr("notifications.refresh"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])

    def reload(self) -> None:
        result = self._service.recent()
        if result.is_failure:
            return
        self._populate(result.value)

    def _populate(self, entries: list[AuditEntryDTO]) -> None:
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = (entry.timestamp, entry.user, entry.module, entry.action, entry.result)
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))
