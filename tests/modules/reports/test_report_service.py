import pytest
from app.infrastructure import ApplicationContext
from app.modules.members.dtos import CreateMemberRequest
from app.modules.members.services import MemberService
from app.modules.reports.services import ReportFormat, ReportService

pytestmark = pytest.mark.integration

_HEADERS = ["#", "Name", "Phone", "Email", "Active"]


@pytest.fixture
def reports(gym_context: ApplicationContext) -> ReportService:
    return gym_context.container.resolve(ReportService)


@pytest.fixture
def _seed_member(gym_context: ApplicationContext) -> None:
    members = gym_context.container.resolve(MemberService)
    members.create_member(CreateMemberRequest(first_name="Reportee", last_name="One"))


@pytest.mark.parametrize("fmt", [ReportFormat.CSV, ReportFormat.XLSX, ReportFormat.PDF])
def test_export_members_creates_nonempty_file(reports, _seed_member, tmp_path, fmt):
    target = tmp_path / f"members.{fmt}"
    result = reports.export_members(target, fmt, headers=_HEADERS, title="Members")
    assert result.is_success
    assert target.exists()
    assert target.stat().st_size > 0


def test_unsupported_format_fails(reports, tmp_path):
    result = reports.export_members(tmp_path / "m.txt", "txt", headers=_HEADERS, title="Members")
    assert result.is_failure


def test_export_payments_csv(reports, tmp_path):
    target = tmp_path / "payments.csv"
    result = reports.export_payments(
        target,
        ReportFormat.CSV,
        headers=["Date", "Member", "Type", "Method", "Amount"],
        title="Payments",
    )
    assert result.is_success
    assert target.exists()
