"""Setting repository (persistence only)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.settings.models.setting import Setting


class SettingRepository(SqlAlchemyRepository[Setting]):
    searchable_fields = ("key",)

    def __init__(self, session: Session) -> None:
        super().__init__(Setting, session)

    def find_by_key(self, key: str) -> Setting | None:
        return self.find_one(key=key)
