"""Locating bundled UI resources (icons) from both source and packaged runs."""

from __future__ import annotations

import sys
from pathlib import Path


def app_icon_path() -> Path | None:
    """Return the application icon path if present.

    Checks next to the executable (packaged build bundles ``assets/``) and the project root
    (running from source). Returns ``None`` if not found, so callers can degrade gracefully.
    """
    candidates = [
        Path(sys.argv[0]).resolve().parent / "assets" / "icon.ico",
        Path(__file__).resolve().parents[2] / "assets" / "icon.ico",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
