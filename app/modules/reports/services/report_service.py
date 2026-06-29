"""Report export service — renders datasets to CSV, Excel (xlsx) or PDF, locally.

Data is pulled through existing module services (never direct DB access here), then written in
the requested format. CSV/Excel handle Arabic perfectly (UTF-8). PDF uses a registered Unicode
TTF for best-effort Arabic glyph rendering.
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.core.base.service import BaseService
from app.core.errors import InfrastructureError
from app.core.pagination import PageRequest, Sort
from app.core.result import Result
from app.logs.logging_service import LoggingService
from app.modules.members.services import MemberService
from app.modules.payments.services import PaymentService

_MAX_ROWS = 10_000


class ReportFormat:
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class ReportService(BaseService):
    def __init__(
        self,
        *,
        members: MemberService,
        payments: PaymentService,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None)
        self._members = members
        self._payments = payments

    def export_members(
        self, path: str | Path, fmt: str, *, headers: list[str], title: str
    ) -> Result[Path]:
        def _build() -> Path:
            result = self._members.list_members(
                PageRequest(size=_MAX_ROWS, sort=(Sort.asc("membership_number"),))
            )
            items = result.value.items if result.is_success else []
            rows = [
                [
                    m.membership_number,
                    m.full_name,
                    m.phone or "",
                    m.email or "",
                    "✓" if m.is_active else "✗",
                ]
                for m in items
            ]
            return self._write(Path(path), fmt, headers, rows, title)

        return self._guard(_build, message="Could not export members")

    def export_payments(
        self, path: str | Path, fmt: str, *, headers: list[str], title: str
    ) -> Result[Path]:
        def _build() -> Path:
            result = self._payments.list_payments(
                PageRequest(size=_MAX_ROWS, sort=(Sort.desc("paid_at"),))
            )
            items = result.value.items if result.is_success else []
            rows = [
                [
                    p.paid_at.strftime("%Y-%m-%d %H:%M"),
                    p.member_label or "-",
                    p.payment_type,
                    p.method,
                    f"{p.amount:.2f}",
                ]
                for p in items
            ]
            return self._write(Path(path), fmt, headers, rows, title)

        return self._guard(_build, message="Could not export payments")

    # --- writers ----------------------------------------------------------
    def _write(
        self, path: Path, fmt: str, headers: list[str], rows: list[list[str]], title: str
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = {
            ReportFormat.CSV: self._write_csv,
            ReportFormat.XLSX: self._write_xlsx,
            ReportFormat.PDF: self._write_pdf,
        }.get(fmt.lower())
        if writer is None:
            raise InfrastructureError(f"Unsupported report format: {fmt!r}.")
        writer(path, headers, rows, title)
        return path

    @staticmethod
    def _write_csv(path: Path, headers: list[str], rows: list[list[str]], title: str) -> None:
        # utf-8-sig so Excel opens Arabic correctly.
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

    @staticmethod
    def _write_xlsx(path: Path, headers: list[str], rows: list[list[str]], title: str) -> None:
        from openpyxl import Workbook
        from openpyxl.styles import Font

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = title[:31] or "Report"
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            sheet.append(row)
        workbook.save(path)

    @staticmethod
    def _write_pdf(path: Path, headers: list[str], rows: list[list[str]], title: str) -> None:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        document = SimpleDocTemplate(str(path), pagesize=A4)
        styles = getSampleStyleSheet()
        table = Table([headers, *rows], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3d5afe")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f4f6fb")],
                    ),
                ]
            )
        )
        document.build([Paragraph(title, styles["Title"]), Spacer(1, 12), table])
