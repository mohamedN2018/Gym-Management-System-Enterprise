"""Typed application configuration.

All behavior-affecting values are configurable (Part 1: *never hardcode values*). Settings are
loaded from environment variables (prefix ``GYM_ERP_``) and an optional ``.env`` file, with
safe offline defaults so the application runs with zero configuration.

Nested settings use a double-underscore delimiter, e.g. ``GYM_ERP_DATABASE__URL``.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    DEFAULT_LOG_LEVEL,
    ENV_DEVELOPMENT,
    ENV_PRODUCTION,
    ENV_TEST,
    LANG_ARABIC,
    LANG_ENGLISH,
    RTL_LANGUAGES,
)

_VALID_ENVIRONMENTS = frozenset({ENV_PRODUCTION, ENV_DEVELOPMENT, ENV_TEST})
_VALID_LANGUAGES = frozenset({LANG_ENGLISH, LANG_ARABIC})
_VALID_THEMES = frozenset({"dark", "light", "system"})
_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    #: Full SQLAlchemy URL. Blank => local SQLite file in the data directory.
    url: str | None = None
    #: Echo emitted SQL to the logger (development only).
    echo: bool = False


class LoggingSettings(BaseSettings):
    """Logging settings."""

    level: str = DEFAULT_LOG_LEVEL

    @field_validator("level", mode="before")
    @classmethod
    def _normalize_level(cls, value: object) -> str:
        level = str(value).upper().strip()
        if level not in _VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level: {value!r}. Expected one of {sorted(_VALID_LOG_LEVELS)}."
            )
        return level


class AppConfig(BaseSettings):
    """Root application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GYM_ERP_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = ENV_PRODUCTION
    language: str = LANG_ENGLISH
    theme: str = "system"
    #: Optional override for the data directory; ``None`` => OS default (see ``AppPaths``).
    data_dir: str | None = None

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    # --- validation -------------------------------------------------------
    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in _VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment: {value!r}. Expected one of {sorted(_VALID_ENVIRONMENTS)}."
            )
        return value

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in _VALID_LANGUAGES:
            raise ValueError(
                f"Invalid language: {value!r}. Expected one of {sorted(_VALID_LANGUAGES)}."
            )
        return value

    @field_validator("theme")
    @classmethod
    def _validate_theme(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in _VALID_THEMES:
            raise ValueError(f"Invalid theme: {value!r}. Expected one of {sorted(_VALID_THEMES)}.")
        return value

    # --- derived ----------------------------------------------------------
    @property
    def is_rtl(self) -> bool:
        return self.language in RTL_LANGUAGES

    @property
    def is_test(self) -> bool:
        return self.environment == ENV_TEST

    @property
    def is_production(self) -> bool:
        return self.environment == ENV_PRODUCTION


def load_config(**overrides: object) -> AppConfig:
    """Build :class:`AppConfig` from environment/.env, applying explicit ``overrides``.

    ``overrides`` win over environment values — used by tests and the composition root.
    """
    return AppConfig(**overrides)
