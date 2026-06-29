"""Configuration and cross-platform path resolution.

- :mod:`app.settings.paths`  — OS-appropriate data directories (Windows/Linux/macOS).
- :mod:`app.settings.config` — typed, env/file-driven :class:`AppConfig` (no hardcoded values).
"""

from app.settings.config import AppConfig, DatabaseSettings, LoggingSettings, load_config
from app.settings.paths import AppPaths

__all__ = [
    "AppConfig",
    "AppPaths",
    "DatabaseSettings",
    "LoggingSettings",
    "load_config",
]
