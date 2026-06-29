import pytest
from app.core.errors import ErrorCode
from app.infrastructure import ApplicationContext
from app.modules.trainers.dtos import CreateTrainerRequest
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
