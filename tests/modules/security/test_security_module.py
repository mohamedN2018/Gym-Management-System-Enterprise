import pytest
from app.core.errors import ErrorCode, PermissionDeniedError
from app.core.pagination import PageRequest
from app.infrastructure import ApplicationContext
from app.modules.security.dtos import CreateUserRequest, LoginRequest
from app.modules.security.permissions import ALL_PERMISSION_CODES, Permissions, Roles
from app.modules.security.repositories import (
    PermissionRepository,
    RoleRepository,
    UserRepository,
)
from app.modules.security.seed import SEED_ADMIN_PASSWORD, SEED_ADMIN_USERNAME
from app.modules.security.services import (
    AuthenticationService,
    AuthorizationService,
    UserService,
)
from app.modules.security.setup import initialize_security

pytestmark = pytest.mark.integration


@pytest.fixture
def auth(security_context: ApplicationContext) -> AuthenticationService:
    return security_context.container.resolve(AuthenticationService)


@pytest.fixture
def authz(security_context: ApplicationContext) -> AuthorizationService:
    return security_context.container.resolve(AuthorizationService)


@pytest.fixture
def users(security_context: ApplicationContext) -> UserService:
    return security_context.container.resolve(UserService)


def _login(auth: AuthenticationService, username: str, password: str):
    return auth.authenticate(LoginRequest(username=username, password=password))


# --- seeding ----------------------------------------------------------------
def test_seed_creates_catalog_roles_and_admin(security_context):
    with security_context.new_unit_of_work() as uow:
        assert PermissionRepository(uow.session).count() == len(ALL_PERMISSION_CODES)
        assert RoleRepository(uow.session).find_by_code(Roles.ADMINISTRATOR) is not None
        assert UserRepository(uow.session).find_by_username(SEED_ADMIN_USERNAME) is not None


def test_seed_is_idempotent(security_context):
    initialize_security(security_context)  # run a second time
    with security_context.new_unit_of_work() as uow:
        assert PermissionRepository(uow.session).count() == len(ALL_PERMISSION_CODES)
        assert UserRepository(uow.session).count() == 1


# --- authentication ---------------------------------------------------------
def test_admin_login_succeeds_with_all_permissions(auth):
    result = _login(auth, SEED_ADMIN_USERNAME, SEED_ADMIN_PASSWORD)
    assert result.is_success
    admin = result.value
    assert Roles.ADMINISTRATOR in admin.roles
    assert set(admin.permissions) == set(ALL_PERMISSION_CODES)


def test_wrong_password_is_invalid(auth):
    result = _login(auth, SEED_ADMIN_USERNAME, "nope")
    assert result.is_failure
    assert result.error.code is ErrorCode.AUTHENTICATION
    assert result.error.details.get("reason") == "invalid"


def test_unknown_user_is_invalid(auth):
    result = _login(auth, "ghost", "whatever")
    assert result.is_failure
    assert result.error.details.get("reason") == "invalid"


def test_empty_credentials_is_validation(auth):
    result = _login(auth, "", "")
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_inactive_account_cannot_login(security_context, auth, users):
    assert users.create_user(
        CreateUserRequest(username="bob", password="Passw0rd!", role_codes=(Roles.RECEPTIONIST,))
    ).is_success
    with security_context.new_unit_of_work() as uow:
        repo = UserRepository(uow.session)
        bob = repo.find_by_username("bob")
        bob.is_active = False
        repo.update(bob)
        uow.commit()

    result = _login(auth, "bob", "Passw0rd!")
    assert result.is_failure
    assert result.error.details.get("reason") == "inactive"


def test_last_login_is_recorded(security_context, auth):
    assert _login(auth, SEED_ADMIN_USERNAME, SEED_ADMIN_PASSWORD).is_success
    with security_context.new_unit_of_work() as uow:
        admin = UserRepository(uow.session).find_by_username(SEED_ADMIN_USERNAME)
        assert admin.last_login_at is not None


# --- authorization (RBAC) ---------------------------------------------------
def test_receptionist_permissions_are_limited(auth, authz, users):
    assert users.create_user(
        CreateUserRequest(username="recep", password="Passw0rd!", role_codes=(Roles.RECEPTIONIST,))
    ).is_success
    recep = _login(auth, "recep", "Passw0rd!").value
    assert authz.has_permission(recep, Permissions.DASHBOARD_VIEW)
    assert not authz.has_permission(recep, Permissions.USERS_MANAGE)
    with pytest.raises(PermissionDeniedError):
        authz.require(recep, Permissions.USERS_MANAGE)


# --- user management --------------------------------------------------------
def test_create_user_duplicate_conflict(users):
    assert users.create_user(CreateUserRequest(username="dup", password="Passw0rd!")).is_success
    second = users.create_user(CreateUserRequest(username="dup", password="Passw0rd!"))
    assert second.is_failure
    assert second.error.code is ErrorCode.CONFLICT


def test_create_user_validation_failure(users):
    result = users.create_user(CreateUserRequest(username="ab", password="short"))
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_create_user_unknown_role(users):
    result = users.create_user(
        CreateUserRequest(username="newuser", password="Passw0rd!", role_codes=("nope",))
    )
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_list_users_paginates(users):
    assert users.create_user(CreateUserRequest(username="user1", password="Passw0rd!")).is_success
    result = users.list_users(PageRequest())
    assert result.is_success
    assert result.value.total == 2  # seeded admin + user1


# --- change password --------------------------------------------------------
def test_change_password_succeeds_and_updates_login(auth, users):
    admin = _login(auth, SEED_ADMIN_USERNAME, SEED_ADMIN_PASSWORD).value
    assert users.change_password(
        admin.id, SEED_ADMIN_PASSWORD, "newpass123", by=admin.id
    ).is_success
    assert _login(auth, SEED_ADMIN_USERNAME, "newpass123").is_success
    assert _login(auth, SEED_ADMIN_USERNAME, SEED_ADMIN_PASSWORD).is_failure


def test_change_password_wrong_current(auth, users):
    admin = _login(auth, SEED_ADMIN_USERNAME, SEED_ADMIN_PASSWORD).value
    result = users.change_password(admin.id, "wrong-current", "newpass123")
    assert result.is_failure
    assert result.error.code is ErrorCode.AUTHENTICATION


def test_change_password_too_short(auth, users):
    admin = _login(auth, SEED_ADMIN_USERNAME, SEED_ADMIN_PASSWORD).value
    result = users.change_password(admin.id, SEED_ADMIN_PASSWORD, "short")
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION
