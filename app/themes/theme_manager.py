"""Application theme manager.

Applies a dark or light Qt stylesheet (QSS) to the whole application and supports runtime
toggling. The ``system`` preference resolves to the OS color scheme when Qt can report it,
falling back to dark. UI code asks the manager to apply/toggle — it never hardcodes colors.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from app.settings.config import AppConfig


class Theme(StrEnum):
    LIGHT = "light"
    DARK = "dark"


# Shared accent + a compact, professional QSS for each theme. Centralized so every widget
# inherits a consistent look (Part 2: *never duplicate UI*).
_DARK_QSS = """
* { font-family: "Segoe UI", "Noto Sans", "Cairo", sans-serif; font-size: 14px; color: #e6e9f0; }
QMainWindow, QDialog { background-color: #161a22; }
QWidget { background-color: transparent; }
QMenuBar { background-color: #11141b; color: #e6e9f0; padding: 2px; }
QMenuBar::item { padding: 6px 12px; background: transparent; }
QMenuBar::item:selected { background-color: #2b3242; border-radius: 6px; }
QMenu { background-color: #1c2230; color: #e6e9f0; border: 1px solid #2b3242; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 4px; }
QMenu::item:selected { background-color: #3d5afe; }
QStatusBar { background-color: #11141b; color: #8b94a6; }
QStatusBar QLabel { color: #8b94a6; }

#Sidebar { background-color: #11141b; border: none; outline: 0; padding: 8px; }
#Sidebar::item { padding: 12px 16px; color: #aab2c5; border-radius: 8px; margin: 2px 6px; }
#Sidebar::item:selected { background-color: #3d5afe; color: #ffffff; }
#Sidebar::item:hover:!selected { background-color: #1f2636; }
#Brand { background-color: #11141b; }
#BrandLabel { font-size: 17px; font-weight: 700; color: #ffffff; padding: 16px 18px 4px 18px; }
#BrandTag { font-size: 11px; color: #6b7280; padding: 0 18px 14px 18px; }

#Content { background-color: #161a22; }
#PageTitle { font-size: 24px; font-weight: 700; color: #ffffff; }

#Card { background-color: #1c2230; border: 1px solid #283041; border-radius: 12px; }
#CardKey { color: #8b94a6; font-size: 13px; }
#CardValue { color: #ffffff; font-weight: 600; }

#KpiCard { background-color: #1c2230; border: 1px solid #283041; border-radius: 14px; }
#KpiIcon { font-size: 26px; }
#KpiValue { color: #ffffff; font-size: 30px; font-weight: 800; }
#KpiKey { color: #8b94a6; font-size: 13px; }

QPushButton { background-color: #3d5afe; color: #ffffff; border: none; padding: 9px 18px; border-radius: 8px; font-weight: 600; }
QPushButton:hover { background-color: #5872ff; }
QPushButton:pressed { background-color: #2f49d8; }
QPushButton:disabled { background-color: #2b3242; color: #5b6472; }
QPushButton:flat { background: transparent; color: #aab2c5; font-weight: 600; }
QPushButton:flat:hover { color: #ffffff; }
QPushButton#DangerButton { background-color: #b3261e; }
QPushButton#DangerButton:hover { background-color: #d4332a; }
QPushButton#DangerButton:pressed { background-color: #8f1d17; }

QLineEdit, QComboBox, QDateEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox { background-color: #11141b; border: 1px solid #2b3242; border-radius: 8px; padding: 8px 10px; color: #e6e9f0; selection-background-color: #3d5afe; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #3d5afe; }
QComboBox QAbstractItemView { background-color: #1c2230; border: 1px solid #2b3242; selection-background-color: #3d5afe; }

QTableWidget, QTableView { background-color: #1c2230; alternate-background-color: #191f2b; gridline-color: #283041; border: 1px solid #283041; border-radius: 10px; }
QHeaderView::section { background-color: #11141b; color: #aab2c5; padding: 8px; border: none; border-bottom: 1px solid #283041; font-weight: 600; }
QTableView::item { padding: 4px; }
QTableView::item:selected { background-color: #3d5afe; color: #ffffff; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2b3242; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #3a4358; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }

#StatusOk { color: #22c55e; font-weight: 700; }
#StatusBad { color: #f87171; font-weight: 700; }
"""

_LIGHT_QSS = """
* { font-family: "Segoe UI", "Noto Sans", "Cairo", sans-serif; font-size: 14px; color: #1f2430; }
QMainWindow, QDialog { background-color: #eef1f7; }
QWidget { background-color: transparent; }
QMenuBar { background-color: #ffffff; color: #1f2430; border-bottom: 1px solid #e2e8f0; padding: 2px; }
QMenuBar::item { padding: 6px 12px; background: transparent; }
QMenuBar::item:selected { background-color: #e8edff; border-radius: 6px; }
QMenu { background-color: #ffffff; color: #1f2430; border: 1px solid #e2e8f0; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 4px; }
QMenu::item:selected { background-color: #3d5afe; color: #ffffff; }
QStatusBar { background-color: #ffffff; color: #5b6472; border-top: 1px solid #e2e8f0; }
QStatusBar QLabel { color: #5b6472; }

#Sidebar { background-color: #ffffff; border: none; outline: 0; padding: 8px; border-right: 1px solid #e7ebf3; }
#Sidebar::item { padding: 12px 16px; color: #424b5a; border-radius: 8px; margin: 2px 6px; }
#Sidebar::item:selected { background-color: #3d5afe; color: #ffffff; }
#Sidebar::item:hover:!selected { background-color: #eef1f8; }
#Brand { background-color: #ffffff; }
#BrandLabel { font-size: 17px; font-weight: 700; color: #1f2430; padding: 16px 18px 4px 18px; }
#BrandTag { font-size: 11px; color: #94a3b8; padding: 0 18px 14px 18px; }

#Content { background-color: #eef1f7; }
#PageTitle { font-size: 24px; font-weight: 700; color: #1f2430; }

#Card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }
#CardKey { color: #5b6472; font-size: 13px; }
#CardValue { color: #1f2430; font-weight: 600; }

#KpiCard { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; }
#KpiIcon { font-size: 26px; }
#KpiValue { color: #1f2430; font-size: 30px; font-weight: 800; }
#KpiKey { color: #5b6472; font-size: 13px; }

QPushButton { background-color: #3d5afe; color: #ffffff; border: none; padding: 9px 18px; border-radius: 8px; font-weight: 600; }
QPushButton:hover { background-color: #2f49d8; }
QPushButton:pressed { background-color: #2740c0; }
QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }
QPushButton:flat { background: transparent; color: #5b6472; font-weight: 600; }
QPushButton:flat:hover { color: #1f2430; }
QPushButton#DangerButton { background-color: #c0271f; }
QPushButton#DangerButton:hover { background-color: #a51f18; }
QPushButton#DangerButton:pressed { background-color: #8f1d17; }

QLineEdit, QComboBox, QDateEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox { background-color: #ffffff; border: 1px solid #d6deea; border-radius: 8px; padding: 8px 10px; color: #1f2430; selection-background-color: #3d5afe; selection-color: #ffffff; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #3d5afe; }
QComboBox QAbstractItemView { background-color: #ffffff; border: 1px solid #d6deea; selection-background-color: #3d5afe; selection-color: #ffffff; }

QTableWidget, QTableView { background-color: #ffffff; alternate-background-color: #f6f8fc; gridline-color: #e7ebf3; border: 1px solid #e2e8f0; border-radius: 10px; }
QHeaderView::section { background-color: #f6f8fc; color: #5b6472; padding: 8px; border: none; border-bottom: 1px solid #e2e8f0; font-weight: 600; }
QTableView::item { padding: 4px; }
QTableView::item:selected { background-color: #3d5afe; color: #ffffff; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #aab2c5; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }

#StatusOk { color: #16a34a; font-weight: 700; }
#StatusBad { color: #dc2626; font-weight: 700; }
"""

_QSS: dict[Theme, str] = {Theme.DARK: _DARK_QSS, Theme.LIGHT: _LIGHT_QSS}


class ThemeManager:
    """Owns the active theme and applies it application-wide."""

    def __init__(self, default: Theme = Theme.DARK) -> None:
        self._current = default

    @classmethod
    def from_config(cls, config: AppConfig) -> ThemeManager:
        return cls(default=cls._resolve(config.theme))

    @property
    def current(self) -> Theme:
        return self._current

    def apply(self, app: QApplication, theme: Theme | None = None) -> Theme:
        """Apply ``theme`` (or the current one) to the application; returns the applied theme."""
        if theme is not None:
            self._current = theme
        app.setStyleSheet(_QSS[self._current])
        return self._current

    def toggle(self, app: QApplication) -> Theme:
        """Switch between dark and light and re-apply."""
        nxt = Theme.LIGHT if self._current is Theme.DARK else Theme.DARK
        return self.apply(app, nxt)

    @staticmethod
    def _resolve(preference: str) -> Theme:
        if preference == Theme.LIGHT.value:
            return Theme.LIGHT
        if preference == Theme.DARK.value:
            return Theme.DARK
        # "system": honor the OS color scheme when Qt can report it (Qt >= 6.5).
        try:
            from PySide6.QtCore import Qt

            scheme = QGuiApplication.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return Theme.LIGHT
        except (AttributeError, RuntimeError):
            pass
        return Theme.DARK
