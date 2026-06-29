"""Gym ERP — offline-first native desktop ERP for gyms.

Top-level package. Layered/Clean architecture: see ``docs/ARCHITECTURE.md``.
Dependencies always point inward: ``ui -> controllers -> services -> repositories -> database``.
"""

from __future__ import annotations

from app.core.constants import APP_VERSION as __version__

__all__ = ["__version__"]
