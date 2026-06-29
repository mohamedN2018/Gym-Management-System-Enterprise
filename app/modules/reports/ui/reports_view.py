"""Reports view — export datasets to CSV/Excel/PDF (presentation only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.bootstrap import ApplicationContext
from app.modules.reports.services import ReportFormat, ReportService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_EXT = {ReportFormat.CSV: "csv", ReportFormat.XLSX: "xlsx", ReportFormat.PDF: "pdf"}
_FILTER = {
    ReportFormat.CSV: "CSV (*.csv)",
    ReportFormat.XLSX: "Excel (*.xlsx)",
    ReportFormat.PDF: "PDF (*.pdf)",
}


class ReportsView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._context = context
        self._loc = context.localization
        self._service: ReportService = context.container.resolve(ReportService)
        self._buttons: list[tuple[QPushButton, str]] = []
        self._section_labels: list[tuple[QLabel, str]] = []
        self._build_ui()
        self._unsubscribe = self._loc.on_change(lambda _c: self._retranslate())
        self.destroyed.connect(lambda: self._unsubscribe())
        self._retranslate()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)

        layout.addWidget(self._build_section("reports.members", self._export_members))
        layout.addWidget(self._build_section("reports.payments", self._export_payments))
        layout.addStretch(1)

    def _build_section(self, label_key: str, handler) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        row = QHBoxLayout(card)
        row.setContentsMargins(18, 14, 18, 14)
        section_label = QLabel()
        section_label.setObjectName("CardValue")
        self._section_labels.append((section_label, label_key))
        row.addWidget(section_label, 1)
        for fmt, key in (
            (ReportFormat.CSV, "reports.export_csv"),
            (ReportFormat.XLSX, "reports.export_excel"),
            (ReportFormat.PDF, "reports.export_pdf"),
        ):
            button = QPushButton()
            button.clicked.connect(lambda _checked=False, f=fmt: handler(f))
            self._buttons.append((button, key))
            row.addWidget(button)
        return card

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("reports.title"))
        for label, key in self._section_labels:
            label.setText(tr(key))
        for button, key in self._buttons:
            button.setText(tr(key))

    # --- export -----------------------------------------------------------
    def _member_headers(self) -> list[str]:
        tr = self._loc.tr
        return [
            tr("members.col_number"),
            tr("members.col_name"),
            tr("members.col_phone"),
            tr("members.col_email"),
            tr("reports.col_active"),
        ]

    def _payment_headers(self) -> list[str]:
        tr = self._loc.tr
        return [
            tr("payments.col_date"),
            tr("payments.col_member"),
            tr("payments.col_type"),
            tr("payments.col_method"),
            tr("payments.col_amount"),
        ]

    def _ask_path(self, dataset: str, fmt: str) -> str | None:
        default = str(self._context.paths.exports_dir / f"{dataset}.{_EXT[fmt]}")
        path, _ = QFileDialog.getSaveFileName(
            self, self._loc.tr("reports.title"), default, _FILTER[fmt]
        )
        return path or None

    def _export_members(self, fmt: str) -> None:
        path = self._ask_path("members", fmt)
        if not path:
            return
        result = self._service.export_members(
            path, fmt, headers=self._member_headers(), title=self._loc.tr("reports.members")
        )
        self._notify(result)

    def _export_payments(self, fmt: str) -> None:
        path = self._ask_path("payments", fmt)
        if not path:
            return
        result = self._service.export_payments(
            path, fmt, headers=self._payment_headers(), title=self._loc.tr("reports.payments")
        )
        self._notify(result)

    def _notify(self, result) -> None:
        title = self._loc.tr("reports.title")
        if result.is_failure:
            QMessageBox.warning(self, title, result.error.message if result.error else "")
            return
        QMessageBox.information(self, title, self._loc.tr("reports.saved"))
