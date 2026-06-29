import pytest
from app.core.errors import ErrorCode
from app.core.pagination import PageRequest
from app.infrastructure import ApplicationContext
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.services import MemberService
from app.modules.members.setup import register_members_services

pytestmark = pytest.mark.integration


@pytest.fixture
def members(security_context: ApplicationContext) -> MemberService:
    # The members table is created by initialize_security's create_all (all models registered).
    register_members_services(security_context.container)
    return security_context.container.resolve(MemberService)


def test_create_member_autogenerates_number(members):
    first = members.create_member(CreateMemberRequest(first_name="Ahmed", last_name="Ali"))
    assert first.is_success
    assert first.value.membership_number == "M00001"
    assert first.value.full_name == "Ahmed Ali"

    second = members.create_member(CreateMemberRequest(first_name="Mona"))
    assert second.is_success
    assert second.value.membership_number == "M00002"


def test_create_member_with_explicit_number(members):
    result = members.create_member(CreateMemberRequest(first_name="VIP", membership_number="VIP-1"))
    assert result.is_success
    assert result.value.membership_number == "VIP-1"


def test_duplicate_membership_number_conflicts(members):
    assert members.create_member(
        CreateMemberRequest(first_name="A", membership_number="DUP")
    ).is_success
    second = members.create_member(CreateMemberRequest(first_name="B", membership_number="DUP"))
    assert second.is_failure
    assert second.error.code is ErrorCode.CONFLICT


def test_validation_rejects_blank_name_and_bad_email(members):
    blank = members.create_member(CreateMemberRequest(first_name="  "))
    assert blank.is_failure
    assert blank.error.code is ErrorCode.VALIDATION

    bad_email = members.create_member(CreateMemberRequest(first_name="Sara", email="not-an-email"))
    assert bad_email.is_failure
    assert bad_email.error.code is ErrorCode.VALIDATION


def test_list_and_search(members):
    members.create_member(CreateMemberRequest(first_name="Treadmill", last_name="User"))
    members.create_member(CreateMemberRequest(first_name="Khaled", phone="01000000000"))

    all_members = members.list_members(PageRequest())
    assert all_members.is_success
    assert all_members.value.total == 2

    found = members.list_members(PageRequest(search="khaled"))
    assert found.is_success
    assert found.value.total == 1
    assert found.value.items[0].first_name == "Khaled"


def test_get_missing_member_is_not_found(members):
    result = members.get_member(999)
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_soft_delete_excludes_from_list(members):
    created = members.create_member(CreateMemberRequest(first_name="Temp"))
    assert created.is_success
    member_id = created.value.id

    assert members.delete_member(member_id).is_success
    listing = members.list_members(PageRequest())
    assert listing.is_success
    assert listing.value.total == 0
    assert members.get_member(member_id).is_failure  # soft-deleted: not found
