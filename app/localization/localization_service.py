"""Localization (i18n) service.

Loads per-language translation catalogs (JSON: key -> text) and resolves keys for the active
language, falling back to English and finally to the key itself so a missing translation is
always visible rather than crashing. Supports runtime language switching with change
notifications so open windows can retranslate without a restart, and reports text direction
for RTL languages such as Arabic.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.constants import LANG_ENGLISH, RTL_LANGUAGES
from app.core.errors import ConfigurationError

#: Listener invoked with the new language code whenever the language changes.
LanguageListener = Callable[[str], None]

#: Human-readable language names (shown in the language menu), keyed by code.
_LANGUAGE_DISPLAY_NAMES: dict[str, str] = {"en": "English", "ar": "العربية"}


class LocalizationService:
    """Holds translation catalogs and the active language."""

    def __init__(
        self,
        catalogs: dict[str, dict[str, str]],
        *,
        default_language: str = LANG_ENGLISH,
        fallback_language: str = LANG_ENGLISH,
    ) -> None:
        if not catalogs:
            raise ConfigurationError("No translation catalogs were provided.")
        self._catalogs = catalogs
        self._fallback = (
            fallback_language if fallback_language in catalogs else next(iter(catalogs))
        )
        self._language = default_language if default_language in catalogs else self._fallback
        self._listeners: list[LanguageListener] = []

    @classmethod
    def from_directory(
        cls,
        directory: str | Path,
        *,
        default_language: str = LANG_ENGLISH,
        fallback_language: str = LANG_ENGLISH,
    ) -> LocalizationService:
        """Load every ``*.json`` catalog in ``directory`` (filename stem is the language code)."""
        catalogs: dict[str, dict[str, str]] = {}
        for path in sorted(Path(directory).glob("*.json")):
            with path.open(encoding="utf-8") as handle:
                catalogs[path.stem] = json.load(handle)
        if not catalogs:
            raise ConfigurationError(f"No translation catalogs found in {directory}.")
        return cls(catalogs, default_language=default_language, fallback_language=fallback_language)

    @classmethod
    def default(
        cls,
        *,
        default_language: str = LANG_ENGLISH,
        fallback_language: str = LANG_ENGLISH,
    ) -> LocalizationService:
        """Load the catalogs bundled with the application (``app/localization/catalogs``)."""
        return cls.from_directory(
            Path(__file__).parent / "catalogs",
            default_language=default_language,
            fallback_language=fallback_language,
        )

    # --- state ------------------------------------------------------------
    @property
    def language(self) -> str:
        return self._language

    @property
    def is_rtl(self) -> bool:
        return self._language in RTL_LANGUAGES

    @property
    def available_languages(self) -> list[str]:
        return list(self._catalogs.keys())

    def display_name(self, language: str | None = None) -> str:
        code = language or self._language
        return _LANGUAGE_DISPLAY_NAMES.get(code, code.upper())

    def is_rtl_language(self, language: str) -> bool:
        return language in RTL_LANGUAGES

    # --- translation ------------------------------------------------------
    def tr(self, key: str, /, **params: Any) -> str:
        """Translate ``key`` for the active language (English fallback, then the key)."""
        text = self._catalogs.get(self._language, {}).get(key)
        if text is None:
            text = self._catalogs.get(self._fallback, {}).get(key, key)
        if params:
            try:
                return text.format(**params)
            except (KeyError, IndexError, ValueError):
                return text
        return text

    # --- language switching ----------------------------------------------
    def set_language(self, language: str) -> None:
        """Switch the active language and notify listeners (no-op if unchanged/unknown)."""
        if language not in self._catalogs:
            raise ConfigurationError(
                f"Unsupported language: {language!r}.",
                details={"available": self.available_languages},
            )
        if language == self._language:
            return
        self._language = language
        for listener in list(self._listeners):
            listener(language)

    def on_change(self, listener: LanguageListener) -> Callable[[], None]:
        """Register a language-change listener; returns an unsubscribe callable."""
        self._listeners.append(listener)

        def _unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _unsubscribe
