"""The application shell window.

A native Qt main window providing the persistent frame — brand, sidebar navigation, content
stack, menus, keyboard shortcuts and status bar — into which business modules plug their views
in later milestones. The initial Home view surfaces real runtime/system status; the theme
toggle, language switch and About dialog are fully functional.

Fully localized: every visible string comes from the :class:`LocalizationService`, and the
window retranslates live (including RTL/LTR mirroring) when the language changes.

This is presentation only: it reads from the :class:`ApplicationContext` and calls services;
it contains no business rules and never touches the database directly (Part 2).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APP_NAME, APP_VERSION
from app.infrastructure.bootstrap import ApplicationContext
from app.localization.localization_service import LocalizationService
from app.themes.theme_manager import ThemeManager
from app.widgets.navigation import KpiCard, NavItem
from app.widgets.resources import app_icon_path

if TYPE_CHECKING:
    from app.modules.security.dtos import AuthenticatedUser


class MainWindow(QMainWindow):
    """Top-level application window / shell."""

    def __init__(
        self,
        context: ApplicationContext,
        theme_manager: ThemeManager,
        current_user: AuthenticatedUser | None = None,
        nav_items: list[NavItem] | None = None,
        kpi_items: list[KpiCard] | None = None,
    ) -> None:
        super().__init__()
        self._context = context
        self._theme = theme_manager
        self._loc: LocalizationService = context.localization
        self._current_user = current_user
        self._nav_items = nav_items or []
        self._kpi_items = kpi_items or []
        self._db_ok = context.verify_database()

        # Widgets/actions whose text must be refreshed on language change.
        self._cards: list[tuple[str, QLabel, Callable[[], str], QLabel]] = []
        self._language_actions: dict[str, QAction] = {}
        self._nav_entries: list[tuple[QListWidgetItem, str, str]] = []

        self.resize(1180, 740)
        self.setMinimumSize(900, 600)
        icon = app_icon_path()
        if icon is not None:
            self.setWindowIcon(QIcon(str(icon)))

        self._build_menu()
        self._build_body()
        self._build_status_bar()

        self._unsubscribe_language = self._loc.on_change(lambda _code: self._apply_language())
        self._apply_language()  # set initial direction + texts

    # --- construction -----------------------------------------------------
    def _build_menu(self) -> None:
        menu = self.menuBar()

        self._menu_file = menu.addMenu("")
        self._act_change_pw = QAction(self)
        self._act_change_pw.triggered.connect(self._on_change_password)
        self._act_change_pw.setEnabled(self._current_user is not None)
        self._menu_file.addAction(self._act_change_pw)
        self._menu_file.addSeparator()
        self._act_quit = QAction(self)
        self._act_quit.setShortcut(QKeySequence.StandardKey.Quit)  # Ctrl+Q / Cmd+Q
        self._act_quit.triggered.connect(self.close)
        self._menu_file.addAction(self._act_quit)

        self._menu_view = menu.addMenu("")
        self._act_theme = QAction(self)
        self._act_theme.setShortcut(QKeySequence("Ctrl+T"))
        self._act_theme.triggered.connect(self._on_toggle_theme)
        self._menu_view.addAction(self._act_theme)

        self._menu_language = menu.addMenu("")
        language_group = QActionGroup(self)
        language_group.setExclusive(True)
        for code in self._loc.available_languages:
            action = QAction(self._loc.display_name(code), self)
            action.setCheckable(True)
            action.setChecked(code == self._loc.language)
            action.triggered.connect(lambda _checked=False, c=code: self._on_set_language(c))
            language_group.addAction(action)
            self._menu_language.addAction(action)
            self._language_actions[code] = action

        self._menu_help = menu.addMenu("")
        self._act_about = QAction(self)
        self._act_about.triggered.connect(self._on_about)
        self._menu_help.addAction(self._act_about)

    def _build_body(self) -> None:
        central = QWidget(self)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._pages = QStackedWidget()
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("Sidebar")
        self._sidebar.setFrameShape(QFrame.Shape.NoFrame)

        # Home (dashboard) is the shell's own landing page; module views follow.
        self._add_page(icon="🏠", label_key="nav.home", widget=self._build_home_page())
        for item in sorted(self._nav_items, key=lambda nav: nav.order):
            if self._permitted(item.permission):
                view = item.factory(self._context, self._current_user)
                self._add_page(icon=item.icon, label_key=item.label_key, widget=view)

        self._sidebar.setCurrentRow(0)
        self._sidebar.currentRowChanged.connect(self._on_nav_changed)

        panel = QWidget()
        panel.setObjectName("Brand")
        panel.setFixedWidth(244)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        brand = QLabel(APP_NAME)  # brand name is not translated
        brand.setObjectName("BrandLabel")
        panel_layout.addWidget(brand)
        self._brand_tag = QLabel()
        self._brand_tag.setObjectName("BrandTag")
        panel_layout.addWidget(self._brand_tag)
        panel_layout.addWidget(self._sidebar, 1)

        layout.addWidget(panel, 0)
        layout.addWidget(self._pages, 1)
        self.setCentralWidget(central)

    def _add_page(self, *, icon: str, label_key: str, widget: QWidget) -> None:
        self._pages.addWidget(widget)
        item = QListWidgetItem()
        self._sidebar.addItem(item)
        self._nav_entries.append((item, label_key, icon))

    def _permitted(self, permission: str | None) -> bool:
        if permission is None or self._current_user is None:
            return True
        return self._current_user.has_permission(permission)

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("Content")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        self._page_title = QLabel()
        self._page_title.setObjectName("PageTitle")
        layout.addWidget(self._page_title)

        grid = QGridLayout()
        grid.setSpacing(16)
        kpis = [
            kpi
            for kpi in sorted(self._kpi_items, key=lambda k: k.order)
            if self._permitted(kpi.permission)
        ]
        if kpis:
            for index, kpi in enumerate(kpis):
                card, key_label, value_label = self._build_kpi_card(kpi.icon)
                self._cards.append((kpi.label_key, key_label, kpi.value_fn, value_label))
                grid.addWidget(card, index // 3, index % 3)
        else:
            for index, (key, value_provider) in enumerate(self._fallback_specs()):
                card, key_label, value_label = self._build_card()
                self._cards.append((key, key_label, value_provider, value_label))
                grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(grid)
        layout.addStretch(1)
        return page

    def _fallback_specs(self) -> list[tuple[str, Callable[[], str]]]:
        """System-info cards shown when no KPI providers are available (e.g. no login)."""
        config = self._context.config
        loc = self._loc
        return [
            ("card.application", lambda: f"{APP_NAME} v{APP_VERSION}"),
            ("card.environment", lambda: loc.tr(f"env.{config.environment}")),
            ("card.language", self._language_value),
            ("card.theme", lambda: loc.tr(f"theme.{self._theme.current.value}")),
            ("card.database", self._database_value),
            ("card.data_directory", lambda: str(self._context.paths.data_dir)),
        ]

    @staticmethod
    def _build_kpi_card(icon: str) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setObjectName("KpiCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(4)

        icon_label = QLabel(icon)
        icon_label.setObjectName("KpiIcon")
        value_label = QLabel()
        value_label.setObjectName("KpiValue")
        key_label = QLabel()
        key_label.setObjectName("KpiKey")

        card_layout.addWidget(icon_label)
        card_layout.addWidget(value_label)
        card_layout.addWidget(key_label)
        return card, key_label, value_label

    @staticmethod
    def _safe_value(value_fn: Callable[[], str]) -> str:
        try:
            return value_fn()
        except Exception:  # noqa: BLE001 - a KPI must never break the dashboard
            return "—"

    def _on_nav_changed(self, index: int) -> None:
        self._pages.setCurrentIndex(index)
        if index == 0:  # returning to Home: refresh KPI values
            for _key, _key_label, value_fn, value_label in self._cards:
                value_label.setText(self._safe_value(value_fn))

    @staticmethod
    def _build_card() -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(6)

        key_label = QLabel()
        key_label.setObjectName("CardKey")
        value_label = QLabel()
        value_label.setObjectName("CardValue")
        value_label.setWordWrap(True)

        card_layout.addWidget(key_label)
        card_layout.addWidget(value_label)
        return card, key_label, value_label

    def _build_status_bar(self) -> None:
        self._status_label = QLabel()
        self._status_label.setObjectName("StatusOk" if self._db_ok else "StatusBad")
        self.statusBar().addWidget(self._status_label)
        self._user_label = QLabel()
        self.statusBar().addPermanentWidget(self._user_label)

    # --- localization -----------------------------------------------------
    def _language_value(self) -> str:
        direction = self._loc.tr("direction.rtl" if self._loc.is_rtl else "direction.ltr")
        return f"{self._loc.display_name()} ({direction})"

    def _database_value(self) -> str:
        return self._loc.tr("status.connected" if self._db_ok else "status.unavailable")

    def _apply_language(self) -> None:
        """Apply text direction and retranslate every visible string."""
        is_rtl = self._loc.is_rtl
        direction = Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight
        app = _running_qapplication()
        if app is not None:
            app.setLayoutDirection(direction)
        self.setLayoutDirection(direction)
        self._retranslate()

    def _retranslate(self) -> None:
        tr = self._loc.tr
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")

        self._menu_file.setTitle(tr("menu.file"))
        self._act_change_pw.setText(tr("menu.change_password"))
        self._act_quit.setText(tr("menu.quit"))
        self._menu_view.setTitle(tr("menu.view"))
        self._act_theme.setText(tr("menu.toggle_theme"))
        self._menu_language.setTitle(tr("menu.language"))
        self._menu_help.setTitle(tr("menu.help"))
        self._act_about.setText(tr("menu.about"))

        self._brand_tag.setText(tr("app.tagline"))
        for item, label_key, icon in self._nav_entries:
            item.setText(f"{icon}  {tr(label_key)}")
        self._page_title.setText(tr("page.dashboard"))

        for key, key_label, value_provider, value_label in self._cards:
            key_label.setText(tr(key))
            value_label.setText(self._safe_value(value_provider))

        self._status_label.setText(f"{tr('status.database')}: {self._database_value()}")
        if self._current_user is not None:
            self._user_label.setText(
                tr("status.signed_in_as", name=self._current_user.display_name)
            )

        for code, action in self._language_actions.items():
            action.setChecked(code == self._loc.language)

    # --- actions ----------------------------------------------------------
    def _on_set_language(self, code: str) -> None:
        self._loc.set_language(code)  # triggers _apply_language via the change listener

    def _on_change_password(self) -> None:
        if self._current_user is None:
            return
        from app.modules.security.services import UserService
        from app.modules.security.ui.change_password_dialog import ChangePasswordDialog

        ChangePasswordDialog(
            user_service=self._context.container.resolve(UserService),
            user_id=self._current_user.id,
            localization=self._loc,
            parent=self,
        ).exec()

    def _on_toggle_theme(self) -> None:
        app = _running_qapplication()
        if app is not None:
            self._theme.toggle(app)
            self._retranslate()  # refresh the theme card value

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            self._loc.tr("about.title", app=APP_NAME),
            f"<b>{APP_NAME}</b> v{APP_VERSION}<br><br>{self._loc.tr('about.body')}",
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override
        self._unsubscribe_language()
        super().closeEvent(event)


def _running_qapplication():
    """Return the running QApplication (kept as a function to ease testing/mocking)."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance()
