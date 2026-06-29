"""Internationalization (i18n) — English (LTR) and Arabic (RTL).

Exposes :class:`~app.localization.localization_service.LocalizationService`, which loads
translation catalogs, resolves keys for the active language (with English fallback), reports
text direction, and notifies listeners so the UI can retranslate live when the language
changes.
"""

from app.localization.localization_service import LocalizationService

__all__ = ["LocalizationService"]
