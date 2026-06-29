"""Theming (dark/light) for the desktop UI.

Exposes :class:`~app.themes.theme_manager.ThemeManager` and the :class:`Theme` enum. QSS
stylesheets are applied application-wide; the manager supports runtime toggling and resolving
the configured ``system``/``dark``/``light`` preference.
"""

from app.themes.theme_manager import Theme, ThemeManager

__all__ = ["Theme", "ThemeManager"]
