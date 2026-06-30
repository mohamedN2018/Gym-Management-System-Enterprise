"""Audit service — reads recent entries from the append-only audit log (JSON lines)."""

from __future__ import annotations

import json

from app.core.base.service import BaseService
from app.core.result import Result
from app.logs.logging_service import LoggingService
from app.modules.audit.dtos import AuditEntryDTO
from app.settings.paths import AppPaths


class AuditService(BaseService):
    def __init__(self, *, paths: AppPaths, logging: LoggingService | None = None) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None)
        self._paths = paths

    def recent(self, limit: int = 300) -> Result[list[AuditEntryDTO]]:
        def _recent() -> list[AuditEntryDTO]:
            path = self._paths.audit_log_file
            if not path.exists():
                return []
            lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
            entries: list[AuditEntryDTO] = []
            for line in reversed(lines):  # newest first
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entries.append(
                    AuditEntryDTO(
                        timestamp=str(data.get("timestamp", "")),
                        user=str(data.get("user", "") if data.get("user") is not None else ""),
                        module=str(data.get("module", "")),
                        action=str(data.get("action", "")),
                        result=str(data.get("result", "")),
                    )
                )
            return entries

        return self._guard(_recent, message="Could not read the audit log")
