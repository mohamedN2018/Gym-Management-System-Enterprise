import pytest
from app.infrastructure import ApplicationContext
from app.modules.settings.models.setting import SettingKeys
from app.modules.settings.services import SettingsService

pytestmark = pytest.mark.integration


@pytest.fixture
def settings(gym_context: ApplicationContext) -> SettingsService:
    return gym_context.container.resolve(SettingsService)


def test_save_then_get_roundtrip(settings):
    assert settings.save(
        {SettingKeys.COMPANY_NAME: "Iron Gym", SettingKeys.COMPANY_CURRENCY: "EGP"}
    ).is_success
    assert settings.get(SettingKeys.COMPANY_NAME) == "Iron Gym"
    assert settings.get(SettingKeys.COMPANY_CURRENCY) == "EGP"


def test_save_updates_existing_key(settings):
    settings.save({SettingKeys.COMPANY_NAME: "Old"})
    settings.save({SettingKeys.COMPANY_NAME: "New"})
    assert settings.get(SettingKeys.COMPANY_NAME) == "New"
    all_values = settings.get_all()
    assert all_values.is_success
    assert all_values.value[SettingKeys.COMPANY_NAME] == "New"


def test_get_returns_default_when_missing(settings):
    assert settings.get("nonexistent.key", default="fallback") == "fallback"
