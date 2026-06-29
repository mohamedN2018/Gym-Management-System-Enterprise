import pytest
from app.core.errors import ConfigurationError
from app.localization.localization_service import LocalizationService

pytestmark = pytest.mark.unit

_CATALOGS = {
    "en": {"greeting": "Hello {name}", "only_en": "EN"},
    "ar": {"greeting": "مرحبا {name}"},
}


def test_default_language_and_formatting():
    loc = LocalizationService(_CATALOGS, default_language="en")
    assert loc.language == "en"
    assert loc.is_rtl is False
    assert loc.tr("greeting", name="Sam") == "Hello Sam"


def test_arabic_is_rtl_and_translates():
    loc = LocalizationService(_CATALOGS, default_language="ar")
    assert loc.is_rtl is True
    assert loc.tr("greeting", name="سام") == "مرحبا سام"


def test_falls_back_to_english_for_missing_key():
    loc = LocalizationService(_CATALOGS, default_language="ar")
    assert loc.tr("only_en") == "EN"


def test_missing_everywhere_returns_key():
    assert LocalizationService(_CATALOGS).tr("nope") == "nope"


def test_set_language_notifies_listeners_then_unsubscribes():
    loc = LocalizationService(_CATALOGS, default_language="en")
    seen: list[str] = []
    unsubscribe = loc.on_change(seen.append)
    loc.set_language("ar")
    assert loc.language == "ar"
    assert seen == ["ar"]
    unsubscribe()
    loc.set_language("en")
    assert seen == ["ar"]  # no further notifications after unsubscribe


def test_unknown_language_raises():
    with pytest.raises(ConfigurationError):
        LocalizationService(_CATALOGS).set_language("fr")


def test_empty_catalogs_raises():
    with pytest.raises(ConfigurationError):
        LocalizationService({})


def test_default_loads_bundled_catalogs_including_arabic():
    loc = LocalizationService.default(default_language="ar")
    assert {"en", "ar"} <= set(loc.available_languages)
    assert loc.is_rtl is True
    assert loc.tr("login.sign_in") == "تسجيل الدخول"
    assert loc.tr("page.dashboard") == "لوحة التحكم"
