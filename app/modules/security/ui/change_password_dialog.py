"""Change-password dialog (presentation only).

Collects current/new/confirm passwords and delegates the change to :class:`UserService`;
maps the service ``Result`` to localized inline errors.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import ErrorCode
from app.localization.localization_service import LocalizationService
from app.modules.security.services import UserService


class ChangePasswordDialog(QDialog):
    def __init__(
        self,
        *,
        user_service: UserService,
        user_id: int,
        localization: LocalizationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = user_service
        self._user_id = user_id
        self._loc = localization
        self.setModal(True)
        self.setMinimumWidth(400)
        tr = localization.tr
        self.setWindowTitle(tr("change_password.title"))

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._current = _password_field()
        self._new = _password_field()
        self._confirm = _password_field()
        form.addRow(tr("change_password.current"), self._current)
        form.addRow(tr("change_password.new"), self._new)
        form.addRow(tr("change_password.confirm"), self._confirm)
        root.addLayout(form)

        self._error = QLabel()
        self._error.setObjectName("StatusBad")
        self._error.setWordWrap(True)
        self._error.setVisible(False)
        root.addWidget(self._error)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(tr("common.cancel"))
        cancel.clicked.connect(self.reject)
        submit = QPushButton(tr("change_password.submit"))
        submit.setDefault(True)
        submit.clicked.connect(self._on_submit)
        buttons.addWidget(cancel)
        buttons.addWidget(submit)
        root.addLayout(buttons)

    def _on_submit(self) -> None:
        if self._new.text() != self._confirm.text():
            self._fail("change_password.mismatch")
            return
        result = self._service.change_password(
            self._user_id, self._current.text(), self._new.text(), by=self._user_id
        )
        if result.is_success:
            QMessageBox.information(
                self, self._loc.tr("change_password.title"), self._loc.tr("change_password.success")
            )
            self.accept()
            return
        error = result.error
        if error is not None and error.code is ErrorCode.AUTHENTICATION:
            self._fail("change_password.current_wrong")
        elif error is not None and error.code is ErrorCode.VALIDATION:
            self._fail("change_password.too_short")
        else:
            self._fail("change_password.failed")

    def _fail(self, key: str) -> None:
        self._error.setText(self._loc.tr(key))
        self._error.setVisible(True)


def _password_field() -> QLineEdit:
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    return field
