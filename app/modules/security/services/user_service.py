"""User management service — create and query users (server-side rules + transactions)."""

from __future__ import annotations

from collections.abc import Callable

from app.core.base.service import BaseService
from app.core.base.validator import min_length
from app.core.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.security.dtos import CreateUserRequest, UserDTO, to_user_dto
from app.modules.security.events import SecurityEvents
from app.modules.security.models.user import User
from app.modules.security.repositories import RoleRepository, UserRepository
from app.modules.security.validators import CreateUserValidator
from app.security.password_hasher import PasswordHasher

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


class UserService(BaseService):
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
        self._validator = CreateUserValidator()

    def create_user(
        self, request: CreateUserRequest, *, created_by: int | None = None
    ) -> Result[UserDTO]:
        return self._guard(
            lambda: self._create_user(request, created_by), message="Could not create user"
        )

    def _create_user(self, request: CreateUserRequest, created_by: int | None) -> UserDTO:
        self._validator.validate_and_raise(request)
        username = request.username.strip()
        with self._uow_factory() as uow:
            users = UserRepository(uow.session)
            roles = RoleRepository(uow.session)
            if users.find_by_username(username, include_deleted=True) is not None:
                raise ConflictError("Username already exists.", details={"field": "username"})
            user = User(
                username=username,
                password_hash=self._hasher.hash(request.password),
                full_name=request.full_name,
                email=request.email,
                created_by=created_by,
            )
            for code in request.role_codes:
                role = roles.find_by_code(code)
                if role is None:
                    raise NotFoundError(f"Role '{code}' not found.", details={"role": code})
                user.roles.append(role)
            users.add(user)
            dto = to_user_dto(user)
            uow.commit()

        if self._logging:
            self._logging.audit(
                action="create",
                module="security.users",
                result="success",
                user=created_by,
                new_value={"username": dto.username, "id": dto.id},
            )
        self._publish(
            Event(SecurityEvents.USER_CREATED, {"user_id": dto.id, "username": dto.username})
        )
        return dto

    def change_password(
        self, user_id: int, current_password: str, new_password: str, *, by: int | None = None
    ) -> Result[None]:
        """Change a user's password after verifying the current one."""

        def _change() -> None:
            if msg := min_length(new_password, 8, "new_password"):
                raise ValidationError(msg, details={"fields": {"new_password": [msg]}})
            with self._uow_factory() as uow:
                users = UserRepository(uow.session)
                user = users.get_or_raise(user_id)
                if not self._hasher.verify(user.password_hash, current_password):
                    raise AuthenticationError(
                        "Current password is incorrect.", details={"reason": "invalid_current"}
                    )
                user.password_hash = self._hasher.hash(new_password)
                user.updated_by = by
                users.update(user)
                uow.commit()
            if self._logging:
                self._logging.audit(
                    action="change_password",
                    module="security.users",
                    result="success",
                    user=by or user_id,
                )
            self._publish(Event(SecurityEvents.USER_PASSWORD_CHANGED, {"user_id": user_id}))

        return self._guard(_change, message="Could not change password")

    def list_users(self, request: PageRequest) -> Result[Page[UserDTO]]:
        return self._guard(lambda: self._list_users(request), message="Could not list users")

    def _list_users(self, request: PageRequest) -> Page[UserDTO]:
        with self._uow_factory() as uow:
            repo = UserRepository(uow.session)
            page = repo.list(request)
            items = [to_user_dto(user) for user in page.items]
            return Page(items=items, total=page.total, page=page.page, size=page.size)
