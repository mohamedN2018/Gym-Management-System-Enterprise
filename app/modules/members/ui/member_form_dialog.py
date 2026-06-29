"""Localized create-member form dialog (presentation only)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.localization.localization_service import LocalizationService
from app.modules.members.dtos import CreateMemberRequest


class MemberFormDialog(QDialog):
    def __init__(self, *, localization: LocalizationService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loc = localization
        self.setModal(True)
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self._number = QLineEdit()
        self._first = QLineEdit()
        self._last = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._national_id = QLineEdit()
        self._address = QLineEdit()

        loc = self._loc
        self._row_labels = {
            self._number: loc.tr("member_form.membership_number"),
            self._first: loc.tr("member_form.first_name"),
            self._last: loc.tr("member_form.last_name"),
            self._phone: loc.tr("member_form.phone"),
            self._email: loc.tr("member_form.email"),
            self._national_id: loc.tr("member_form.national_id"),
            self._address: loc.tr("member_form.address"),
        }
        self._number.setPlaceholderText(loc.tr("member_form.membership_number_placeholder"))
        for field, label in self._row_labels.items():
            form.addRow(label, field)
        root.addLayout(form)

        self._error = QLabel()
        self._error.setObjectName("StatusBad")
        self._error.setWordWrap(True)
        self._error.setVisible(False)
        root.addWidget(self._error)

        buttons = QDialogButtonBox()
        self._save = buttons.addButton(
            loc.tr("common.save"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.addButton(loc.tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        self._save.clicked.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.setWindowTitle(loc.tr("member_form.title"))

    def _on_accept(self) -> None:
        if not self._first.text().strip():
            self._error.setText(self._loc.tr("member_form.first_name_required"))
            self._error.setVisible(True)
            self._first.setFocus()
            return
        self.accept()

    def to_request(self) -> CreateMemberRequest:
        def _value(field: QLineEdit) -> str | None:
            return field.text().strip() or None

        return CreateMemberRequest(
            first_name=self._first.text().strip(),
            last_name=_value(self._last),
            phone=_value(self._phone),
            email=_value(self._email),
            national_id=_value(self._national_id),
            address=_value(self._address),
            membership_number=_value(self._number),
        )
