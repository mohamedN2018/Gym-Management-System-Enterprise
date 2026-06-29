"""Settings service — read and persist key/value application settings."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from app.core.base.service import BaseService
from app.core.events import Event, EventBus
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.settings.models.setting import Setting
from app.modules.settings.repositories import SettingRepository

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]

SETTINGS_CHANGED = "settings.changed"


class SettingsService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None, events=events)
        self._uow_factory = uow_factory
        self._logging = logging

    def get(self, key: str, default: str | None = None) -> str | None:
        with self._uow_factory() as uow:
            setting = SettingRepository(uow.session).find_by_key(key)
            return setting.value if setting is not None and setting.value is not None else default

    def get_all(self) -> Result[dict[str, str]]:
        def _all() -> dict[str, str]:
            with self._uow_factory() as uow:
                rows = SettingRepository(uow.session).find()
                return {row.key: row.value or "" for row in rows}

        return self._guard(_all, message="Could not load settings")

    def save(self, values: Mapping[str, str], *, updated_by: int | None = None) -> Result[None]:
        def _save() -> None:
            with self._uow_factory() as uow:
                repo = SettingRepository(uow.session)
                for key, value in values.items():
                    setting = repo.find_by_key(key)
                    if setting is None:
                        repo.add(Setting(key=key, value=value, created_by=updated_by))
                    else:
                        setting.value = value
                        setting.updated_by = updated_by
                        repo.update(setting)
                uow.commit()
            if self._logging:
                self._logging.audit(
                    action="update",
                    module="settings",
                    result="success",
                    user=updated_by,
                    new_value={"keys": list(values.keys())},
                )
            self._publish(Event(SETTINGS_CHANGED, {"keys": list(values.keys())}))

        return self._guard(_save, message="Could not save settings")
