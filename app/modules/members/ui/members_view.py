"""Members view — search + table + add (presentation only).

Calls :class:`MemberService` through the DI container and renders DTOs. No business rules or
direct database access (Part 2). Fully localized with live retranslation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
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
from app.modules.members.dtos import MemberDTO
from app.modules.members.services import MemberService
from app.modules.members.ui.member_form_dialog import MemberFormDialog
from app.modules.members.ui.member_qr_dialog import MemberQrDialog
from app.services.qr_code_service import QrCodeService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_PAGE_SIZE = 200
_COLUMNS = ("members.col_number", "members.col_name", "members.col_phone", "members.col_email")


class MembersView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._context = context
        self._loc = context.localization
        self._current_user = current_user
        self._service: MemberService = context.container.resolve(MemberService)
        self._qr: QrCodeService = context.container.resolve(QrCodeService)
        self._members_data: list[MemberDTO] = []

        self._build_ui()
        self._unsubscribe_language = self._loc.on_change(lambda _code: self._retranslate())
        self.destroyed.connect(lambda: self._unsubscribe_language())
        self._retranslate()
        self.reload()

    # --- construction -----------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self._search = QLineEdit()
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self.reload)
        toolbar.addWidget(self._search, 1)
        self._qr_button = QPushButton()
        self._qr_button.clicked.connect(self._on_qr)
        toolbar.addWidget(self._qr_button, 0)
        self._add_button = QPushButton()
        self._add_button.clicked.connect(self._on_add)
        toolbar.addWidget(self._add_button, 0)
        layout.addLayout(toolbar)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

        self._empty = QLabel()
        self._empty.setObjectName("CardKey")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)
        layout.addWidget(self._empty)

    # --- localization -----------------------------------------------------
    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("members.title"))
        self._search.setPlaceholderText(tr("members.search_placeholder"))
        self._add_button.setText(tr("members.add"))
        self._qr_button.setText(tr("members.qr"))
        self._empty.setText(tr("members.empty"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])

    # --- data -------------------------------------------------------------
    def reload(self) -> None:
        request = PageRequest(
            search=self._search.text(), size=_PAGE_SIZE, sort=(Sort.asc("membership_number"),)
        )
        result = self._service.list_members(request)
        if result.is_failure:
            self._show_error(result.error.message if result.error else "")
            return
        self._populate(result.value.items)

    def _populate(self, members: list[MemberDTO]) -> None:
        self._members_data = members
        self._table.setRowCount(len(members))
        for row, member in enumerate(members):
            values = (
                member.membership_number,
                member.full_name,
                member.phone or "",
                member.email or "",
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))
        self._empty.setVisible(not members)
        self._table.setVisible(bool(members))

    # --- actions ----------------------------------------------------------
    def _on_add(self) -> None:
        dialog = MemberFormDialog(localization=self._loc, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._service.create_member(dialog.to_request(), created_by=created_by)
        if result.is_failure:
            self._show_error(result.error.message if result.error else "")
            return
        self.reload()

    def _on_qr(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._members_data):
            QMessageBox.information(
                self, self._loc.tr("members.title"), self._loc.tr("member_qr.select_first")
            )
            return
        member = self._members_data[row]
        dialog = MemberQrDialog(
            localization=self._loc,
            qr_service=self._qr,
            membership_number=member.membership_number,
            member_name=member.full_name,
            export_dir=self._context.paths.exports_dir,
            parent=self,
        )
        dialog.exec()

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, self._loc.tr("members.create_failed"), message)
