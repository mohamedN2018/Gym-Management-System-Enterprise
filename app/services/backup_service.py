"""Local database backup & restore.

Uses SQLite's online backup API (consistent even while the app is running, WAL-safe) to copy
the database to a timestamped file under the data directory's ``backups/`` folder, and to
restore a chosen backup back into the live database. All local; no cloud (Part 1).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from app.core.base.service import BaseService
from app.core.errors import InfrastructureError, NotFoundError
from app.core.result import Result
from app.logs.logging_service import LoggingService
from app.settings.paths import AppPaths

_BACKUP_PREFIX = "gym_erp_"
_BACKUP_SUFFIX = ".db"


class BackupService(BaseService):
    def __init__(
        self,
        *,
        paths: AppPaths,
        now_provider: Callable[[], datetime],
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None)
        self._paths = paths
        self._now = now_provider
        self._logging = logging

    def create_backup(self) -> Result[Path]:
        def _create() -> Path:
            source_db = self._paths.database_file
            if not source_db.exists():
                raise InfrastructureError("There is no database to back up yet.")
            self._paths.backups_dir.mkdir(parents=True, exist_ok=True)
            stamp = self._now().strftime("%Y%m%d_%H%M%S")
            destination = self._paths.backups_dir / f"{_BACKUP_PREFIX}{stamp}{_BACKUP_SUFFIX}"
            self._copy(source_db, destination)
            if self._logging:
                self._logging.audit(
                    action="backup",
                    module="maintenance",
                    result="success",
                    new_value={"file": destination.name},
                )
            return destination

        return self._guard(_create, message="Could not create backup")

    def list_backups(self) -> list[Path]:
        if not self._paths.backups_dir.exists():
            return []
        files = self._paths.backups_dir.glob(f"{_BACKUP_PREFIX}*{_BACKUP_SUFFIX}")
        return sorted(files, key=lambda p: p.name, reverse=True)

    def restore_backup(self, backup_path: str | Path) -> Result[None]:
        def _restore() -> None:
            source = Path(backup_path)
            if not source.exists():
                raise NotFoundError("The selected backup file does not exist.")
            self._paths.database_dir.mkdir(parents=True, exist_ok=True)
            self._copy(source, self._paths.database_file)
            if self._logging:
                self._logging.audit(
                    action="restore",
                    module="maintenance",
                    result="success",
                    new_value={"file": source.name},
                )

        return self._guard(_restore, message="Could not restore backup")

    @staticmethod
    def _copy(source: Path, destination: Path) -> None:
        src = sqlite3.connect(str(source))
        dst = sqlite3.connect(str(destination))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
