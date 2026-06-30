import pytest
from app.infrastructure import ApplicationContext
from app.modules.audit.services import AuditService
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.services import MemberService

pytestmark = pytest.mark.integration


@pytest.fixture
def audit(gym_context: ApplicationContext) -> AuditService:
    return gym_context.container.resolve(AuditService)


def test_recent_returns_a_list(audit):
    result = audit.recent()
    assert result.is_success
    assert isinstance(result.value, list)


def test_audited_action_appears_in_log(gym_context, audit):
    # Creating a member writes an audit entry.
    members = gym_context.container.resolve(MemberService)
    assert members.create_member(CreateMemberRequest(first_name="Audited")).is_success

    result = audit.recent()
    assert result.is_success
    assert any("members" in entry.module for entry in result.value)
