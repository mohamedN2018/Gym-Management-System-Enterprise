"""Application identity and framework-level defaults.

Single source of truth for values that must not be scattered as magic literals across the
codebase (Part 1: *never hardcode values*). Business-configurable values live in
``AppConfig`` / settings tables instead; this module holds only stable framework constants.
"""

from __future__ import annotations

from typing import Final

# --- Application identity -------------------------------------------------
APP_NAME: Final[str] = "Gym ERP"
APP_SLUG: Final[str] = "gym-erp"
APP_VERSION: Final[str] = "0.1.0"
ORG_NAME: Final[str] = "Gym ERP"
ORG_DOMAIN: Final[str] = "gymerp.local"

# --- Persistence ----------------------------------------------------------
DEFAULT_SQLITE_FILENAME: Final[str] = "gym_erp.db"
#: SQLAlchemy URL scheme used when no explicit database URL is configured.
SQLITE_URL_SCHEME: Final[str] = "sqlite+pysqlite"

# --- Pagination -----------------------------------------------------------
DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_PAGE_SIZE: Final[int] = 500
MIN_PAGE_NUMBER: Final[int] = 1

# --- Security / encryption ------------------------------------------------
ENCRYPTION_KEY_FILENAME: Final[str] = "secret.key"

# --- Logging --------------------------------------------------------------
LOG_FILENAME: Final[str] = "gym_erp.log"
AUDIT_LOG_FILENAME: Final[str] = "audit.log"
LOG_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MiB per file
LOG_BACKUP_COUNT: Final[int] = 10
DEFAULT_LOG_LEVEL: Final[str] = "INFO"

# --- Local storage layout (relative to the resolved data directory) -------
#: Subdirectories created under the application data directory at startup.
DATA_SUBDIRS: Final[tuple[str, ...]] = (
    "database",
    "backups",
    "logs",
    "photos",
    "reports",
    "exports",
    "imports",
    "temp",
)

# --- Environment names ----------------------------------------------------
ENV_PRODUCTION: Final[str] = "production"
ENV_DEVELOPMENT: Final[str] = "development"
ENV_TEST: Final[str] = "test"

# --- Supported UI languages (BCP-47-ish short codes) ----------------------
LANG_ENGLISH: Final[str] = "en"
LANG_ARABIC: Final[str] = "ar"
#: Languages rendered right-to-left.
RTL_LANGUAGES: Final[frozenset[str]] = frozenset({LANG_ARABIC})
