"""Authorization service — RBAC permission checks against an authenticated principal."""

from __future__ import annotations

from app.core.base.service import BaseService
from app.core.errors import PermissionDeniedError
from app.logs.logging_service import LoggingService
from app.modules.security.dtos import AuthenticatedUser


class AuthorizationService(BaseService):
    def __init__(self, *, logging: LoggingService | None = None) -> None:
        super().__init__(logger=logging.get_logger(__name__) if logging else None)

    def has_permission(self, principal: AuthenticatedUser, code: str) -> bool:
        return principal.has_permission(code)

    def has_any(self, principal: AuthenticatedUser, *codes: str) -> bool:
        return principal.has_any_permission(*codes)

    def require(self, principal: AuthenticatedUser, code: str) -> None:
        """Raise :class:`PermissionDeniedError` if ``principal`` lacks ``code``."""
        if not principal.has_permission(code):
            self._logger.warning("Permission denied for user %s: %s", principal.username, code)
            raise PermissionDeniedError(
                "You do not have permission to perform this action.",
                details={"permission": code},
            )
