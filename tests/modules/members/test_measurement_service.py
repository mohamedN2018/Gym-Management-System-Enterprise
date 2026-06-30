from decimal import Decimal

import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.members.dtos import CreateMeasurementRequest, CreateMemberRequest
from app.modules.members.services import MeasurementService, MemberService
from app.modules.members.setup import register_members_services

pytestmark = pytest.mark.integration


@pytest.fixture
def services(security_context: ApplicationContext) -> tuple[MemberService, MeasurementService]:
    register_members_services(security_context.container)
    container = security_context.container
    return container.resolve(MemberService), container.resolve(MeasurementService)


def _member_id(members: MemberService) -> int:
    created = members.create_member(CreateMemberRequest(first_name="Ahmed", last_name="Ali"))
    assert created.is_success
    return created.value.id


def test_record_computes_bmi(services):
    members, measurements = services
    member_id = _member_id(members)

    result = measurements.record_measurement(
        CreateMeasurementRequest(
            member_id=member_id, weight_kg=Decimal("80"), height_cm=Decimal("180")
        )
    )
    assert result.is_success
    # 80 / (1.8 * 1.8) = 24.69
    assert result.value.bmi == Decimal("24.69")
    assert result.value.member_id == member_id


def test_bmi_is_none_without_both_metrics(services):
    members, measurements = services
    member_id = _member_id(members)

    weight_only = measurements.record_measurement(
        CreateMeasurementRequest(member_id=member_id, weight_kg=Decimal("75"))
    )
    assert weight_only.is_success
    assert weight_only.value.bmi is None


def test_list_returns_newest_first(services):
    members, measurements = services
    member_id = _member_id(members)

    first = measurements.record_measurement(
        CreateMeasurementRequest(
            member_id=member_id, weight_kg=Decimal("90"), height_cm=Decimal("180")
        )
    )
    assert first.is_success
    second = measurements.record_measurement(
        CreateMeasurementRequest(
            member_id=member_id, weight_kg=Decimal("85"), height_cm=Decimal("180")
        )
    )
    assert second.is_success

    listing = measurements.list_measurements(member_id)
    assert listing.is_success
    assert len(listing.value) == 2
    assert listing.value[0].weight_kg == Decimal("85")

    latest = measurements.latest(member_id)
    assert latest.is_success
    assert latest.value is not None
    assert latest.value.weight_kg == Decimal("85")


def test_empty_metrics_is_validation_error(services):
    members, measurements = services
    member_id = _member_id(members)

    result = measurements.record_measurement(CreateMeasurementRequest(member_id=member_id))
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_unknown_member_is_not_found(services):
    _members, measurements = services
    result = measurements.record_measurement(
        CreateMeasurementRequest(member_id=999, weight_kg=Decimal("70"), height_cm=Decimal("170"))
    )
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_bmi_of_helper():
    assert MeasurementService.bmi_of(Decimal("80"), Decimal("180")) == Decimal("24.69")
    assert MeasurementService.bmi_of(None, Decimal("180")) is None
    assert MeasurementService.bmi_of(Decimal("80"), None) is None
    assert MeasurementService.bmi_of(Decimal("80"), Decimal("0")) is None
