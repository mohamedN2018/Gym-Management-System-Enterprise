"""Navigation contributions for the application shell.

A :class:`NavItem` lets a module contribute a sidebar entry + view without the shell importing
the module. The composition root (``launcher``) collects nav items from modules and hands them
to :class:`~app.widgets.main_window.MainWindow`, which builds the sidebar, gating each entry by
the signed-in user's permissions. This keeps the shell decoupled and the system plugin-ready.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import QWidget


@dataclass(frozen=True, slots=True)
class NavItem:
    """A sidebar navigation entry and the view it shows.

    ``factory`` is called as ``factory(context, current_user)`` to lazily build the view.
    ``permission`` (if set) hides the entry from users lacking it.
    """

    key: str
    label_key: str
    icon: str
    factory: Callable[..., QWidget]
    permission: str | None = None
    order: int = 100


@dataclass(frozen=True, slots=True)
class KpiCard:
    """A dashboard metric. ``value_fn`` is called to (re)compute the displayed value."""

    label_key: str
    icon: str
    value_fn: Callable[[], str]
    permission: str | None = None
    order: int = 100
