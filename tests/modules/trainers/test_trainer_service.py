import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.trainers.dtos import CreateTrainerRequest, UpdateTrainerRequest
from app.modules.trainers.services import TrainerService

pytestmark = pytest.mark.integration


@pytest.fixture
def trainers(gym_context: ApplicationContext) -> TrainerService:
    return gym_context.container.resolve(TrainerService)


def test_create_trainer_autogenerates_code(trainers):
    result = trainers.create_trainer(
        CreateTrainerRequest(first_name="Sami", last_name="Adel", specialty="CrossFit")
    )
    assert result.is_success
    assert result.value.code == "T0001"
    assert result.value.full_name == "Sami Adel"


def test_create_trainer_requires_first_name(trainers):
    result = trainers.create_trainer(CreateTrainerRequest(first_name="  "))
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_list_trainers(trainers):
    trainers.create_trainer(CreateTrainerRequest(first_name="A"))
    trainers.create_trainer(CreateTrainerRequest(first_name="B"))
    result = trainers.list_trainers()
    assert result.is_success
    assert result.value.total == 2


def test_update_trainer_changes_fields_but_keeps_code(trainers):
    created = trainers.create_trainer(
        CreateTrainerRequest(first_name="Sami", last_name="Adel", specialty="CrossFit")
    )
    assert created.is_success
    trainer = created.value

    result = trainers.update_trainer(
        trainer.id,
        UpdateTrainerRequest(
            first_name="Samir",
            last_name="Adel",
            phone="0123456789",
            email="samir@example.com",
            specialty="Yoga",
        ),
    )
    assert result.is_success
    assert result.value.id == trainer.id
    assert result.value.code == trainer.code  # code is immutable
    assert result.value.full_name == "Samir Adel"
    assert result.value.phone == "0123456789"
    assert result.value.email == "samir@example.com"
    assert result.value.specialty == "Yoga"


def test_update_trainer_validates_input(trainers):
    created = trainers.create_trainer(CreateTrainerRequest(first_name="Sami"))
    assert created.is_success
    result = trainers.update_trainer(created.value.id, UpdateTrainerRequest(first_name="   "))
    assert result.is_failure
    assert result.error.code is ErrorCode.VALIDATION


def test_update_trainer_missing_returns_not_found(trainers):
    result = trainers.update_trainer(9999, UpdateTrainerRequest(first_name="Ghost"))
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND


def test_delete_trainer_soft_deletes(trainers):
    created = trainers.create_trainer(CreateTrainerRequest(first_name="Sami"))
    assert created.is_success

    result = trainers.delete_trainer(created.value.id)
    assert result.is_success

    listing = trainers.list_trainers()
    assert listing.is_success
    assert listing.value.total == 0


def test_delete_trainer_missing_returns_not_found(trainers):
    result = trainers.delete_trainer(9999)
    assert result.is_failure
    assert result.error.code is ErrorCode.NOT_FOUND
