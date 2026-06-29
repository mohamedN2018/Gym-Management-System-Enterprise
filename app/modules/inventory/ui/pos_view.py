"""POS view — build a cart from products and check out (presentation only)."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.pagination import PageRequest, Sort
from app.infrastructure.bootstrap import ApplicationContext
from app.modules.inventory.dtos import CartLine, ProductDTO
from app.modules.inventory.services import PosService, ProductService

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser

_PRODUCT_COLS = ("products.col_name", "products.col_price", "products.col_stock")
_CART_COLS = ("pos.col_product", "pos.col_qty", "pos.col_total")


class PosView(QWidget):
    def __init__(
        self, context: ApplicationContext, current_user: AuthenticatedUser | None = None
    ) -> None:
        super().__init__()
        self._loc = context.localization
        self._current_user = current_user
        self._products_service: ProductService = context.container.resolve(ProductService)
        self._pos: PosService = context.container.resolve(PosService)
        self._products: list[ProductDTO] = []
        self._cart: dict[int, int] = {}  # product_id -> quantity

        self._build_ui()
        self._unsubscribe = self._loc.on_change(lambda _c: self._retranslate())
        self.destroyed.connect(lambda: self._unsubscribe())
        self._retranslate()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)

        self._products_table = QTableWidget(0, len(_PRODUCT_COLS))
        _configure_table(self._products_table)
        self._products_table.itemDoubleClicked.connect(lambda _i: self._add_selected())
        layout.addWidget(self._products_table, 1)

        add_bar = QHBoxLayout()
        add_bar.addStretch(1)
        self._add_to_cart = QPushButton()
        self._add_to_cart.clicked.connect(self._add_selected)
        add_bar.addWidget(self._add_to_cart)
        layout.addLayout(add_bar)

        self._cart_table = QTableWidget(0, len(_CART_COLS))
        _configure_table(self._cart_table)
        layout.addWidget(self._cart_table, 1)

        footer = QHBoxLayout()
        self._total_label = QLabel()
        self._total_label.setObjectName("CardValue")
        footer.addWidget(self._total_label, 1)
        self._clear = QPushButton()
        self._clear.clicked.connect(self._clear_cart)
        footer.addWidget(self._clear)
        self._checkout = QPushButton()
        self._checkout.setDefault(True)
        self._checkout.clicked.connect(self._on_checkout)
        footer.addWidget(self._checkout)
        layout.addLayout(footer)

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self._title.setText(tr("pos.title"))
        self._add_to_cart.setText(tr("pos.add_to_cart"))
        self._clear.setText(tr("pos.clear"))
        self._checkout.setText(tr("pos.checkout"))
        self._products_table.setHorizontalHeaderLabels([tr(k) for k in _PRODUCT_COLS])
        self._cart_table.setHorizontalHeaderLabels([tr(k) for k in _CART_COLS])
        self._refresh_cart()

    def reload(self) -> None:
        result = self._products_service.list_products(
            PageRequest(size=300, sort=(Sort.asc("name"),))
        )
        if result.is_failure:
            return
        self._products = result.value.items
        self._products_table.setRowCount(len(self._products))
        for row, product in enumerate(self._products):
            values = (product.name, f"{product.price:.2f}", str(product.stock_quantity))
            for column, value in enumerate(values):
                self._products_table.setItem(row, column, QTableWidgetItem(value))

    def _add_selected(self) -> None:
        row = self._products_table.currentRow()
        if row < 0 or row >= len(self._products):
            return
        product = self._products[row]
        self._cart[product.id] = self._cart.get(product.id, 0) + 1
        self._refresh_cart()

    def _refresh_cart(self) -> None:
        by_id = {p.id: p for p in self._products}
        rows = [(pid, qty) for pid, qty in self._cart.items() if pid in by_id]
        self._cart_table.setRowCount(len(rows))
        total = Decimal("0")
        for index, (pid, qty) in enumerate(rows):
            product = by_id[pid]
            line_total = product.price * qty
            total += line_total
            for column, value in enumerate((product.name, str(qty), f"{line_total:.2f}")):
                self._cart_table.setItem(index, column, QTableWidgetItem(value))
        self._total_label.setText(f"{self._loc.tr('pos.total')}: {total:.2f}")

    def _clear_cart(self) -> None:
        self._cart.clear()
        self._refresh_cart()

    def _on_checkout(self) -> None:
        lines = [CartLine(product_id=pid, quantity=qty) for pid, qty in self._cart.items()]
        if not lines:
            return
        created_by = self._current_user.id if self._current_user is not None else None
        result = self._pos.checkout(lines, created_by=created_by)
        if result.is_failure:
            QMessageBox.warning(
                self, self._loc.tr("pos.title"), result.error.message if result.error else ""
            )
            return
        QMessageBox.information(
            self,
            self._loc.tr("pos.title"),
            self._loc.tr("pos.completed", total=f"{result.value.total:.2f}"),
        )
        self._clear_cart()
        self.reload()


def _configure_table(table: QTableWidget) -> None:
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
