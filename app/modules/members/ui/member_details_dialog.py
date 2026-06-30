"""Member details dialog — profile, active subscription, and measurements/BMI.

Presentation only: aggregates data from the member, membership and measurement services and
lets staff record a new body measurement. Contains no business rules (Part 2).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.bootstrap import ApplicationContext
from app.modules.members.dtos import CreateMeasurementRequest, MeasurementDTO, MemberDTO
from app.modules.members.services import MeasurementService
from app.modules.membership.services import MembershipService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "member_details.col_date",
    "member_details.col_weight",
    "member_details.col_height",
    "member_details.col_bmi",
)


class MemberDetailsDialog(QDialog):
    def __init__(
        self,
        *,
        context: ApplicationContext,
        member: MemberDTO,
        current_user: AuthenticatedUser | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._loc = context.localization
        self._member = member
        self._current_user = current_user
        self._measurements: MeasurementService = context.container.resolve(MeasurementService)
        self._membership: MembershipService = context.container.resolve(MembershipService)

        tr = self._loc.tr
        self.setWindowTitle(f"{member.membership_number} — {member.full_name}")
        self.setModal(True)
        self.setMinimumWidth(560)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        heading = QLabel(member.full_name)
        heading.setObjectName("PageTitle")
        root.addWidget(heading)

        # Profile.
        profile = QFormLayout()
        profile.addRow(tr("member_qr.number"), QLabel(member.membership_number))
        profile.addRow(tr("member_form.phone"), QLabel(member.phone or "—"))
        profile.addRow(tr("member_form.email"), QLabel(member.email or "—"))
        profile.addRow(tr("member_form.national_id"), QLabel(member.national_id or "—"))
        profile.addRow(tr("member_form.gender"), QLabel(self._gender_label(member.gender)))
        profile.addRow(tr("member_form.birth_date"), QLabel(self._birth_label(member)))
        profile.addRow(tr("member_form.address"), QLabel(member.address or "—"))
        if member.notes:
            notes = QLabel(member.notes)
            notes.setWordWrap(True)
            profile.addRow(tr("member_form.notes"), notes)
        root.addLayout(profile)

        # Subscription status.
        self._subscription = QLabel()
        self._subscription.setObjectName("CardValue")
        root.addWidget(self._subscription)

        # Measurements: record form.
        self._bmi_label = QLabel()
        self._bmi_label.setObjectName("CardValue")
        root.addWidget(self._bmi_label)
        record_row = QHBoxLayout()
        self._weight = QLineEdit()
        self._weight.setPlaceholderText(tr("member_details.weight"))
        self._height = QLineEdit()
        self._height.setPlaceholderText(tr("member_details.height"))
        self._record_btn = QPushButton(tr("member_details.record"))
        self._record_btn.clicked.connect(self._on_record)
        record_row.addWidget(self._weight)
        record_row.addWidget(self._height)
        record_row.addWidget(self._record_btn)
        root.addLayout(record_row)

        self._error = QLabel()
        self._error.setObjectName("StatusBad")
        self._error.setVisible(False)
        root.addWidget(self._error)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])
        root.addWidget(self._table, 1)

        close = QPushButton(tr("common.cancel"))
        close.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(close)
        root.addLayout(close_row)

        self._load_subscription()
        self._reload_measurements()

    def _gender_label(self, gender: str | None) -> str:
        if gender not in ("male", "female"):
            return "—"
        return self._loc.tr(f"member_form.gender_{gender}")

    def _birth_label(self, member: MemberDTO) -> str:
        if member.birth_date is None:
            return "—"
        age = member.age
        text = member.birth_date.strftime("%Y-%m-%d")
        if age is not None:
            text = self._loc.tr("member_details.birth_with_age", date=text, age=age)
        return text

    def _load_subscription(self) -> None:
        tr = self._loc.tr
        result = self._membership.active_subscription(self._member.id)
        active = result.value if result.is_success else None
        if active is not None:
            self._subscription.setText(
                tr("member_details.active_sub", plan=active.plan_name, days=active.remaining_days)
            )
            self._subscription.setObjectName("StatusOk")
        else:
            self._subscription.setText(tr("member_details.no_sub"))
            self._subscription.setObjectName("StatusBad")

    def _reload_measurements(self) -> None:
        result = self._measurements.list_measurements(self._member.id)
        rows = result.value if result.is_success else []
        self._populate(rows)
        latest = rows[0] if rows else None
        bmi = latest.bmi if latest else None
        self._bmi_label.setText(
            self._loc.tr("member_details.latest_bmi", bmi=f"{bmi:.2f}" if bmi is not None else "—")
        )

    def _populate(self, rows: list[MeasurementDTO]) -> None:
        self._table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (
                row.measured_at.strftime("%Y-%m-%d %H:%M"),
                f"{row.weight_kg:.1f}" if row.weight_kg is not None else "—",
                f"{row.height_cm:.0f}" if row.height_cm is not None else "—",
                f"{row.bmi:.2f}" if row.bmi is not None else "—",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(index, column, item)

    def _on_record(self) -> None:
        self._error.setVisible(False)
        weight = self._parse(self._weight.text())
        height = self._parse(self._height.text())
        if weight is False or height is False:
            self._error.setText(self._loc.tr("member_details.invalid"))
            self._error.setVisible(True)
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._measurements.record_measurement(
            CreateMeasurementRequest(member_id=self._member.id, weight_kg=weight, height_cm=height),
            created_by=created_by,
        )
        if result.is_failure:
            self._error.setText(result.error.message if result.error else "")
            self._error.setVisible(True)
            return
        self._weight.clear()
        self._height.clear()
        self._reload_measurements()

    @staticmethod
    def _parse(text: str) -> Decimal | None | bool:
        text = text.strip()
        if not text:
            return None
        try:
            return Decimal(text)
        except InvalidOperation:
            return False
