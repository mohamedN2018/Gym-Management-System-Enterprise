"""Security module event topics (published on the application :class:`EventBus`)."""

from __future__ import annotations


class SecurityEvents:
    USER_CREATED = "security.user.created"
    USER_UPDATED = "security.user.updated"
    USER_LOGGED_IN = "security.user.logged_in"
    USER_LOGIN_FAILED = "security.user.login_failed"
    USER_PASSWORD_CHANGED = "security.user.password_changed"
