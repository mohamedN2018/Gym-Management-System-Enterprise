"""Cross-platform application path resolution.

Resolves the per-user data directory using OS conventions and exposes the local storage
layout (Part 2: *store locally*; *never store inside source code*). No third-party dependency
— the small amount of platform logic is implemented directly to avoid an extra package.

Layout under the data directory::

    <data_dir>/
      database/   backups/   logs/   photos/
      reports/    exports/   imports/  temp/
      secret.key
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core.constants import (
    APP_NAME,
    APP_SLUG,
    AUDIT_LOG_FILENAME,
    DATA_SUBDIRS,
    DEFAULT_SQLITE_FILENAME,
    ENCRYPTION_KEY_FILENAME,
    LOG_FILENAME,
    ORG_NAME,
)


def _default_data_dir() -> Path:
    """Return the OS-appropriate per-user data directory for the application."""
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / ORG_NAME / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    # Linux / other POSIX: honor XDG.
    xdg = os.environ.get("XDG_DATA_HOME")
    root = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return root / APP_SLUG


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Resolved, absolute application paths. Construct via :meth:`resolve`."""

    data_dir: Path

    @classmethod
    def resolve(cls, override: str | os.PathLike[str] | None = None) -> AppPaths:
        """Resolve paths, honoring an explicit ``override`` (e.g. ``GYM_ERP_DATA_DIR``)."""
        base = Path(override).expanduser() if override else _default_data_dir()
        return cls(data_dir=base.resolve())

    # --- directories ------------------------------------------------------
    @property
    def database_dir(self) -> Path:
        return self.data_dir / "database"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def photos_dir(self) -> Path:
        return self.data_dir / "photos"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def imports_dir(self) -> Path:
        return self.data_dir / "imports"

    @property
    def temp_dir(self) -> Path:
        return self.data_dir / "temp"

    # --- files ------------------------------------------------------------
    @property
    def database_file(self) -> Path:
        return self.database_dir / DEFAULT_SQLITE_FILENAME

    @property
    def encryption_key_file(self) -> Path:
        return self.data_dir / ENCRYPTION_KEY_FILENAME

    @property
    def log_file(self) -> Path:
        return self.logs_dir / LOG_FILENAME

    @property
    def audit_log_file(self) -> Path:
        return self.logs_dir / AUDIT_LOG_FILENAME

    # --- lifecycle --------------------------------------------------------
    def ensure(self) -> AppPaths:
        """Create the data directory and all standard subdirectories if missing."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for name in DATA_SUBDIRS:
            (self.data_dir / name).mkdir(parents=True, exist_ok=True)
        return self
