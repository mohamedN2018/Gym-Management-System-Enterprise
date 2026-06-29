"""Notifications view — lists actionable alerts (presentation only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.bootstrap import ApplicationContext
from app.modules.notifications.dtos import AlertDTO, AlertSeverity
from app.modules.notifications.services import NotificationService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_SEVERITY_OBJECT = {
    AlertSeverity.DANGER: "StatusBad",
    AlertSeverity.WARNING: "CardValue",
    AlertSeverity.INFO: "CardKey",
}


class NotificationsView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._service: NotificationService = context.container.resolve(NotificationService)
        self._build_ui()
        self._unsubscribe = self._loc.on_change(lambda _c: self._retranslate())
        self.destroyed.connect(lambda: self._unsubscribe())
        self._retranslate()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)

        self._refresh = QPushButton()
        self._refresh.clicked.connect(self.reload)
        self._refresh.setMaximumWidth(160)
        layout.addWidget(self._refresh)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list = QWidget()
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setSpacing(10)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._list)
        layout.addWidget(scroll, 1)

        self._empty = QLabel()
        self._empty.setObjectName("CardKey")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty)

    def _retranslate(self) -> None:
        self._title.setText(self._loc.tr("notifications.title"))
        self._refresh.setText(self._loc.tr("notifications.refresh"))
        self._empty.setText(self._loc.tr("notifications.empty"))
        self.reload()

    def reload(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        result = self._service.get_alerts()
        alerts = result.value if result.is_success else []
        for alert in alerts:
            self._list_layout.addWidget(self._build_card(alert))
        self._empty.setVisible(not alerts)

    def _build_card(self, alert: AlertDTO) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(16, 12, 16, 12)
        message = QLabel(self._loc.tr(alert.key, **alert.params))
        message.setObjectName(_SEVERITY_OBJECT.get(alert.severity, "CardValue"))
        message.setWordWrap(True)
        inner.addWidget(message)
        return card
