"""Member QR dialog — shows a member's QR code and exports it as PNG (presentation only)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.localization.localization_service import LocalizationService
from app.services.qr_code_service import QrCodeService


class MemberQrDialog(QDialog):
    def __init__(
        self,
        *,
        localization: LocalizationService,
        qr_service: QrCodeService,
        membership_number: str,
        member_name: str,
        export_dir: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._loc = localization
        self._number = membership_number
        self._export_dir = export_dir
        self._png = qr_service.generate_png(membership_number, box_size=10, border=2)

        tr = localization.tr
        self.setWindowTitle(tr("member_qr.title"))
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        name = QLabel(member_name)
        name.setObjectName("PageTitle")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(name)

        number_label = QLabel(f"{tr('member_qr.number')}: {membership_number}")
        number_label.setObjectName("CardKey")
        number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(number_label)

        pixmap = QPixmap()
        pixmap.loadFromData(self._png)
        image = QLabel()
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setPixmap(pixmap)
        root.addWidget(image)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close = QPushButton(tr("common.cancel"))
        close.clicked.connect(self.reject)
        export = QPushButton(tr("member_qr.export"))
        export.setDefault(True)
        export.clicked.connect(self._on_export)
        buttons.addWidget(close)
        buttons.addWidget(export)
        root.addLayout(buttons)

    def _on_export(self) -> None:
        default_path = str(self._export_dir / f"{self._number}.png")
        path, _ = QFileDialog.getSaveFileName(
            self, self._loc.tr("member_qr.export"), default_path, "PNG (*.png)"
        )
        if not path:
            return
        Path(path).write_bytes(self._png)
        QMessageBox.information(
            self, self._loc.tr("member_qr.title"), self._loc.tr("member_qr.saved")
        )
