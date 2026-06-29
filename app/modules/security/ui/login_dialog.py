"""Localized login dialog (presentation only).

Collects credentials and delegates verification to :class:`AuthenticationService`; it contains
no authentication logic itself (Part 2). Fully localized with a live language switch and
RTL/LTR mirroring. On success, the authenticated principal is available as
:attr:`authenticated_user` and the dialog is accepted.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APP_NAME
from app.core.errors import ErrorCode
from app.localization.localization_service import LocalizationService
from app.modules.security.dtos import AuthenticatedUser, LoginRequest
from app.modules.security.services import AuthenticationService


class LoginDialog(QDialog):
    def __init__(
        self,
        *,
        authentication_service: AuthenticationService,
        localization: LocalizationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth = authentication_service
        self._loc = localization
        self.authenticated_user: AuthenticatedUser | None = None

        self.setModal(True)
        self.setMinimumWidth(440)

        self._language_buttons: dict[str, QPushButton] = {}
        self._build_ui()

        self._unsubscribe_language = self._loc.on_change(lambda _code: self._apply_language())
        self._apply_language()

    # --- construction -----------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 32)
        root.setSpacing(14)

        # Language switch row.
        lang_row = QHBoxLayout()
        lang_row.setSpacing(6)
        lang_row.addStretch(1)
        for code in self._loc.available_languages:
            button = QPushButton(self._loc.display_name(code))
            button.setFlat(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, c=code: self._loc.set_language(c))
            self._language_buttons[code] = button
            lang_row.addWidget(button)
        root.addLayout(lang_row)

        self._brand = QLabel(APP_NAME)
        self._brand.setObjectName("BrandLabel")
        self._brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._brand)

        self._heading = QLabel()
        self._heading.setObjectName("PageTitle")
        self._heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._heading)

        self._subheading = QLabel()
        self._subheading.setObjectName("CardKey")
        self._subheading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._subheading)

        root.addSpacing(8)

        self._username_label = QLabel()
        self._username_label.setObjectName("CardKey")
        root.addWidget(self._username_label)
        self._username = QLineEdit()
        self._username.returnPressed.connect(lambda: self._password.setFocus())
        root.addWidget(self._username)

        self._password_label = QLabel()
        self._password_label.setObjectName("CardKey")
        root.addWidget(self._password_label)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.returnPressed.connect(self._on_submit)
        root.addWidget(self._password)

        self._error = QLabel()
        self._error.setObjectName("StatusBad")
        self._error.setWordWrap(True)
        self._error.setVisible(False)
        root.addWidget(self._error)

        root.addSpacing(6)
        self._submit = QPushButton()
        self._submit.setDefault(True)
        self._submit.clicked.connect(self._on_submit)
        root.addWidget(self._submit)

    # --- localization -----------------------------------------------------
    def _apply_language(self) -> None:
        is_rtl = self._loc.is_rtl
        direction = Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight
        app = _running_qapplication()
        if app is not None:
            app.setLayoutDirection(direction)
        self.setLayoutDirection(direction)
        self._retranslate()

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self.setWindowTitle(tr("login.title"))
        self._heading.setText(tr("login.heading"))
        self._subheading.setText(tr("login.subheading", app=APP_NAME))
        self._username_label.setText(tr("login.username"))
        self._username.setPlaceholderText(tr("login.username_placeholder"))
        self._password_label.setText(tr("login.password"))
        self._password.setPlaceholderText(tr("login.password_placeholder"))
        self._submit.setText(tr("login.sign_in"))
        if self._error.isVisible():
            self._error.setText(tr(self._error.property("error_key") or "login.error_invalid"))

    # --- behavior ---------------------------------------------------------
    def _show_error(self, key: str) -> None:
        self._error.setProperty("error_key", key)
        self._error.setText(self._loc.tr(key))
        self._error.setVisible(True)

    def _on_submit(self) -> None:
        request = LoginRequest(username=self._username.text(), password=self._password.text())
        result = self._auth.authenticate(request)
        if result.is_success:
            self.authenticated_user = result.value
            self.accept()
            return

        error = result.error
        if error is not None and error.code == ErrorCode.VALIDATION:
            self._show_error("login.error_required")
        elif error is not None and error.details.get("reason") == "inactive":
            self._show_error("login.error_inactive")
        else:
            self._show_error("login.error_invalid")
        self._password.clear()
        self._password.setFocus()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override
        self._unsubscribe_language()
        super().closeEvent(event)


def _running_qapplication():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance()
