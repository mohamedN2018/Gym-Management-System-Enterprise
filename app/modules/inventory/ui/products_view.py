"""Products view — list inventory products + add (presentation only)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
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
from app.modules.inventory.dtos import CreateProductRequest, ProductDTO
from app.modules.inventory.services import ProductService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_COLUMNS = ("products.col_sku", "products.col_name", "products.col_price", "products.col_stock")


class _ProductFormDialog(QDialog):
    def __init__(self, localization: LocalizationService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loc = localization
        self.setModal(True)
        self.setMinimumWidth(380)
        tr = localization.tr
        self.setWindowTitle(tr("product_form.title"))

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit()
        self._price = QLineEdit("0")
        self._stock = QLineEdit("0")
        self._category = QLineEdit()
        form.addRow(tr("product_form.name"), self._name)
        form.addRow(tr("product_form.price"), self._price)
        form.addRow(tr("product_form.stock"), self._stock)
        form.addRow(tr("product_form.category"), self._category)
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
        if not self._name.text().strip():
            return self._fail("product_form.name_required")
        try:
            self._parsed_price = Decimal(self._price.text().strip() or "0")
            self._parsed_stock = int(self._stock.text().strip() or "0")
        except (InvalidOperation, ValueError):
            return self._fail("product_form.invalid_numbers")
        if self._parsed_price < 0 or self._parsed_stock < 0:
            return self._fail("product_form.invalid_numbers")
        self.accept()
        return None

    def _fail(self, key: str) -> None:
        self._error.setText(self._loc.tr(key))
        self._error.setVisible(True)

    def to_request(self) -> CreateProductRequest:
        return CreateProductRequest(
            name=self._name.text().strip(),
            price=self._parsed_price,
            stock_quantity=self._parsed_stock,
            category=self._category.text().strip() or None,
        )


class ProductsView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._current_user = current_user
        self._service: ProductService = context.container.resolve(ProductService)
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
        self._title.setText(tr("products.title"))
        self._add.setText(tr("products.add"))
        self._table.setHorizontalHeaderLabels([tr(key) for key in _COLUMNS])

    def reload(self) -> None:
        result = self._service.list_products(PageRequest(size=300, sort=(Sort.asc("name"),)))
        if result.is_failure:
            return
        self._populate(result.value.items)

    def _populate(self, products: list[ProductDTO]) -> None:
        self._table.setRowCount(len(products))
        for row, product in enumerate(products):
            values = (
                product.sku,
                product.name,
                f"{product.price:.2f}",
                str(product.stock_quantity),
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))

    def _on_add(self) -> None:
        dialog = _ProductFormDialog(self._loc, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._service.create_product(dialog.to_request(), created_by=created_by)
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("products.title"), result.error.message if result.error else ""
            )
            return
        self.reload()
