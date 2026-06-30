"""Localized create/edit member form dialog (presentation only).

When constructed with ``member=None`` it collects a new member; when given an existing
:class:`MemberDTO` it pre-fills every field for editing (the membership number is shown
read-only because it is printed on cards/QR codes and must stay stable).
"""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.localization.localization_service import LocalizationService
from app.modules.members.dtos import CreateMemberRequest, MemberDTO, UpdateMemberRequest

#: Canonical gender codes persisted in the database (UI labels are localized).
_GENDER_CODES = (None, "male", "female")


class MemberFormDialog(QDialog):
    def __init__(
        self,
        *,
        localization: LocalizationService,
        member: MemberDTO | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._loc = localization
        self._member = member
        self.setModal(True)
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        loc = self._loc

        self._number = QLineEdit()
        self._number.setPlaceholderText(loc.tr("member_form.membership_number_placeholder"))
        self._first = QLineEdit()
        self._last = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._national_id = QLineEdit()

        self._gender = QComboBox()
        for code in _GENDER_CODES:
            key = "member_form.gender_none" if code is None else f"member_form.gender_{code}"
            self._gender.addItem(loc.tr(key), code)

        self._birth = QDateEdit()
        self._birth.setCalendarPopup(True)
        self._birth.setDisplayFormat("yyyy-MM-dd")
        self._birth.setMinimumDate(QDate(1900, 1, 1))
        self._birth.setMaximumDate(QDate.currentDate())
        self._birth.setSpecialValueText("—")  # minimum date renders as "no date"
        self._birth.setDate(self._birth.minimumDate())

        self._address = QLineEdit()
        self._notes = QPlainTextEdit()
        self._notes.setFixedHeight(64)

        form.addRow(loc.tr("member_form.membership_number"), self._number)
        form.addRow(loc.tr("member_form.first_name"), self._first)
        form.addRow(loc.tr("member_form.last_name"), self._last)
        form.addRow(loc.tr("member_form.phone"), self._phone)
        form.addRow(loc.tr("member_form.email"), self._email)
        form.addRow(loc.tr("member_form.national_id"), self._national_id)
        form.addRow(loc.tr("member_form.gender"), self._gender)
        form.addRow(loc.tr("member_form.birth_date"), self._birth)
        form.addRow(loc.tr("member_form.address"), self._address)
        form.addRow(loc.tr("member_form.notes"), self._notes)
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

        if member is None:
            self.setWindowTitle(loc.tr("member_form.title"))
        else:
            self.setWindowTitle(loc.tr("member_form.edit_title"))
            self._prefill(member)

    # --- edit mode --------------------------------------------------------
    def _prefill(self, member: MemberDTO) -> None:
        self._number.setText(member.membership_number)
        self._number.setReadOnly(True)  # immutable: printed on cards/QR
        self._first.setText(member.first_name)
        self._last.setText(member.last_name or "")
        self._phone.setText(member.phone or "")
        self._email.setText(member.email or "")
        self._national_id.setText(member.national_id or "")
        index = self._gender.findData(member.gender)
        self._gender.setCurrentIndex(index if index >= 0 else 0)
        if member.birth_date is not None:
            self._birth.setDate(
                QDate(member.birth_date.year, member.birth_date.month, member.birth_date.day)
            )
        self._address.setText(member.address or "")
        self._notes.setPlainText(member.notes or "")

    # --- submission -------------------------------------------------------
    def _on_accept(self) -> None:
        if not self._first.text().strip():
            self._error.setText(self._loc.tr("member_form.first_name_required"))
            self._error.setVisible(True)
            self._first.setFocus()
            return
        self.accept()

    def _birth_date(self):
        if self._birth.date() == self._birth.minimumDate():
            return None
        return self._birth.date().toPython()

    @staticmethod
    def _text(field: QLineEdit) -> str | None:
        return field.text().strip() or None

    def to_request(self) -> CreateMemberRequest:
        return CreateMemberRequest(
            first_name=self._first.text().strip(),
            last_name=self._text(self._last),
            phone=self._text(self._phone),
            email=self._text(self._email),
            national_id=self._text(self._national_id),
            gender=self._gender.currentData(),
            birth_date=self._birth_date(),
            address=self._text(self._address),
            notes=self._notes.toPlainText().strip() or None,
            membership_number=self._text(self._number),
        )

    def to_update_request(self) -> UpdateMemberRequest:
        return UpdateMemberRequest(
            first_name=self._first.text().strip(),
            last_name=self._text(self._last),
            phone=self._text(self._phone),
            email=self._text(self._email),
            national_id=self._text(self._national_id),
            gender=self._gender.currentData(),
            birth_date=self._birth_date(),
            address=self._text(self._address),
            notes=self._notes.toPlainText().strip() or None,
        )
