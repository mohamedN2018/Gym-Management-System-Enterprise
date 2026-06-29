"""Trainers view — list + add (presentation only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.pagination import PageRequest, Sort
from app.infrastructure.bootstrap import ApplicationContext
from app.localization.localization_service import LocalizationService
from app.modules.trainers.dtos import CreateTrainerRequest, TrainerDTO
from app.modules.trainers.services import TrainerService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = (
    "trainers.col_code",
    "trainers.col_name",
    "trainers.col_phone",
    "trainers.col_specialty",
)


class _TrainerFormDialog(QDialog):
    def __init__(self, localization: LocalizationService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loc = localization
        self.setModal(True)
        self.setMinimumWidth(400)
        tr = localization.tr
        self.setWindowTitle(tr("trainer_form.title"))

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._first = QLineEdit()
        self._last = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._specialty = QLineEdit()
        form.addRow(tr("trainer_form.first_name"), self._first)
        form.addRow(tr("trainer_form.last_name"), self._last)
        form.addRow(tr("trainer_form.phone"), self._phone)
        form.addRow(tr("trainer_form.email"), self._email)
        form.addRow(tr("trainer_form.specialty"), self._specialty)
        root.addLayout(form)

        self._error = QLabel()
        self._error.setObjectName("StatusBad")
        self._error.setVisible(False)
        root.addWidget(self._error)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(tr("common.cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(tr("common.save"))
        save.setDefault(True)
        save.clicked.connect(self._on_accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def _on_accept(self) -> None:
        if not self._first.text().strip():
            self._error.setText(self._loc.tr("trainer_form.first_name_required"))
            self._error.setVisible(True)
            return
        self.accept()

    def to_request(self) -> CreateTrainerRequest:
        def _value(field: QLineEdit) -> str | None:
            return field.text().strip() or None

        return CreateTrainerRequest(
            first_name=self._first.text().strip(),
            last_name=_value(self._last),
            phone=_value(self._phone),
            email=_value(self._email),
            specialty=_value(self._specialty),
        )


class TrainersView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._current_user = current_user
        self._service: TrainerService = context.container.resolve(TrainerService)
        self._build_ui()
        self._unsubscribe = self._loc.on_change(lambda _c: self._retranslate())
        self.destroyed.connect(lambda: self._unsubscribe())
        self._retranslate()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)

        bar = QHBoxLayout()
        bar.addStretch(1)
        self._add = QPushButton()
        self._add.clicked.connect(self._on_add)
        bar.addWidget(self._add)
        layout.addLayout(bar)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("trainers.title"))
        self._add.setText(tr("trainers.add"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])

    def reload(self) -> None:
        result = self._service.list_trainers(PageRequest(size=200, sort=(Sort.asc("code"),)))
        if result.is_failure:
            return
        self._populate(result.value.items)

    def _populate(self, trainers: list[TrainerDTO]) -> None:
        self._table.setRowCount(len(trainers))
        for row, trainer in enumerate(trainers):
            values = (trainer.code, trainer.full_name, trainer.phone or "", trainer.specialty or "")
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))

    def _on_add(self) -> None:
        dialog = _TrainerFormDialog(self._loc, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._service.create_trainer(dialog.to_request(), created_by=created_by)
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("trainers.title"), result.error.message if result.error else ""
            )
            return
        self.reload()
