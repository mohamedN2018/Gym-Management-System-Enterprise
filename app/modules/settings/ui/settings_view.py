"""Settings view — edit company settings (presentation only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.bootstrap import ApplicationContext
from app.modules.settings.models.setting import SettingKeys
from app.modules.settings.services import SettingsService
from app.services.backup_service import BackupService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser


class SettingsView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._current_user = current_user
        self._service: SettingsService = context.container.resolve(SettingsService)
        self._backup: BackupService = context.container.resolve(BackupService)
        self._context = context
        self._build_ui()
        self._unsubscribe = self._loc.on_change(lambda _c: self._retranslate())
        self.destroyed.connect(lambda: self._unsubscribe())
        self._retranslate()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)

        form = QFormLayout()
        form.setSpacing(12)
        self._company_name = QLineEdit()
        self._currency = QLineEdit()
        self._phone = QLineEdit()
        self._row_company = QLabel()
        self._row_currency = QLabel()
        self._row_phone = QLabel()
        form.addRow(self._row_company, self._company_name)
        form.addRow(self._row_currency, self._currency)
        form.addRow(self._row_phone, self._phone)
        layout.addLayout(form)

        bar = QHBoxLayout()
        bar.addStretch(1)
        self._save = QPushButton()
        self._save.setDefault(True)
        self._save.clicked.connect(self._on_save)
        bar.addWidget(self._save)
        layout.addLayout(bar)

        # --- Maintenance: backup / restore ---------------------------------
        self._maintenance_title = QLabel()
        self._maintenance_title.setObjectName("PageTitle")
        layout.addSpacing(8)
        layout.addWidget(self._maintenance_title)
        maintenance = QFrame()
        maintenance.setObjectName("Card")
        maintenance_row = QHBoxLayout(maintenance)
        maintenance_row.setContentsMargins(18, 14, 18, 14)
        self._maintenance_hint = QLabel()
        self._maintenance_hint.setObjectName("CardKey")
        self._maintenance_hint.setWordWrap(True)
        maintenance_row.addWidget(self._maintenance_hint, 1)
        self._backup_btn = QPushButton()
        self._backup_btn.clicked.connect(self._on_backup)
        self._restore_btn = QPushButton()
        self._restore_btn.clicked.connect(self._on_restore)
        maintenance_row.addWidget(self._backup_btn)
        maintenance_row.addWidget(self._restore_btn)
        layout.addWidget(maintenance)
        layout.addStretch(1)

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("settings.title"))
        self._row_company.setText(tr("settings.company_name"))
        self._row_currency.setText(tr("settings.currency"))
        self._row_phone.setText(tr("settings.company_phone"))
        self._save.setText(tr("common.save"))
        self._maintenance_title.setText(tr("settings.maintenance"))
        self._maintenance_hint.setText(tr("settings.maintenance_hint"))
        self._backup_btn.setText(tr("settings.backup_now"))
        self._restore_btn.setText(tr("settings.restore"))

    def _load(self) -> None:
        result = self._service.get_all()
        values = result.value if result.is_success else {}
        self._company_name.setText(values.get(SettingKeys.COMPANY_NAME, ""))
        self._currency.setText(values.get(SettingKeys.COMPANY_CURRENCY, ""))
        self._phone.setText(values.get(SettingKeys.COMPANY_PHONE, ""))

    def _on_save(self) -> None:
        updated_by = self._current_user.id if self._current_user is not None else None
        result = self._service.save(
            {
                SettingKeys.COMPANY_NAME: self._company_name.text().strip(),
                SettingKeys.COMPANY_CURRENCY: self._currency.text().strip(),
                SettingKeys.COMPANY_PHONE: self._phone.text().strip(),
            },
            updated_by=updated_by,
        )
        title = self._loc.tr("settings.title")
        if result.is_failure:
            QMessageBox.warning(self, title, result.error.message if result.error else "")
            return
        QMessageBox.information(self, title, self._loc.tr("settings.saved"))

    def _on_backup(self) -> None:
        result = self._backup.create_backup()
        title = self._loc.tr("settings.maintenance")
        if result.is_failure:
            QMessageBox.warning(self, title, result.error.message if result.error else "")
            return
        QMessageBox.information(
            self, title, self._loc.tr("settings.backup_done", file=result.value.name)
        )

    def _on_restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._loc.tr("settings.restore"),
            str(self._context.paths.backups_dir),
            "Database (*.db)",
        )
        if not path:
            return
        confirm = QMessageBox.question(
            self, self._loc.tr("settings.restore"), self._loc.tr("settings.restore_confirm")
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        result = self._backup.restore_backup(path)
        title = self._loc.tr("settings.maintenance")
        if result.is_failure:
            QMessageBox.warning(self, title, result.error.message if result.error else "")
            return
        QMessageBox.information(self, title, self._loc.tr("settings.restore_done"))
