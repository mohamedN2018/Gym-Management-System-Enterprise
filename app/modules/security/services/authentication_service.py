"""Authentication service — verifies credentials and produces the authenticated principal.

Owns the login workflow: validation, credential verification (argon2id, fail-closed),
active/locked checks, transparent password rehashing, ``last_login`` tracking, audit logging
and event publication. Returns a :class:`Result` so the UI never deals with exceptions.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.core.base.service import BaseService
from app.core.errors import AuthenticationError
from app.core.events import Event, EventBus
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.security.dtos import AuthenticatedUser, LoginRequest, to_authenticated_user
from app.modules.security.events import SecurityEvents
from app.modules.security.repositories import UserRepository
from app.modules.security.validators import LoginValidator
from app.security.password_hasher import PasswordHasher

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


class AuthenticationService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        password_hasher: PasswordHasher,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(
            logger=logging.get_logger(__name__) if logging else None,
            events=events,
        )
        self._uow_factory = uow_factory
        self._hasher = password_hasher
        self._logging = logging
        self._validator = LoginValidator()

    def authenticate(self, request: LoginRequest) -> Result[AuthenticatedUser]:
        """Verify credentials. On success returns the authenticated principal."""
        return self._guard(lambda: self._authenticate(request), message="Authentication failed")

    def _authenticate(self, request: LoginRequest) -> AuthenticatedUser:
        self._validator.validate_and_raise(request)
        username = request.username.strip()
        with self._uow_factory() as uow:
            repo = UserRepository(uow.session)
            user = repo.find_by_username(username)
            if user is None or not self._hasher.verify(user.password_hash, request.password):
                self._record_failure(username, "invalid")
                raise AuthenticationError(
                    "Invalid username or password.", details={"reason": "invalid"}
                )
            if not user.can_authenticate:
                self._record_failure(username, "inactive")
                raise AuthenticationError(
                    "This account is inactive.", details={"reason": "inactive"}
                )
            # Transparently upgrade the hash if argon2 parameters have changed.
            if self._hasher.needs_rehash(user.password_hash):
                user.password_hash = self._hasher.hash(request.password)
            user.last_login_at = datetime.now(UTC)
            repo.update(user)
            principal = to_authenticated_user(user)
            uow.commit()

        self._record_success(principal)
        return principal

    def _record_success(self, principal: AuthenticatedUser) -> None:
        if self._logging:
            self._logging.audit(
                action="login",
                module="security",
                result="success",
                user=principal.username,
                new_value={"user_id": principal.id},
            )
        self._publish(
            Event(
                SecurityEvents.USER_LOGGED_IN,
                {"user_id": principal.id, "username": principal.username},
            )
        )

    def _record_failure(self, username: str, reason: str) -> None:
        if self._logging:
            self._logging.audit(
                action="login",
                module="security",
                result="failure",
                user=username,
                new_value={"reason": reason},
            )
        self._publish(
            Event(SecurityEvents.USER_LOGIN_FAILED, {"username": username, "reason": reason})
        )
