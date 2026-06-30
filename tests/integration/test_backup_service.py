import pytest
from app.infrastructure import ApplicationContext
from app.services.backup_service import BackupService

pytestmark = pytest.mark.integration


@pytest.fixture
def backup(gym_context: ApplicationContext) -> BackupService:
    return gym_context.container.resolve(BackupService)


def test_create_backup_writes_a_file_and_lists_it(backup):
    result = backup.create_backup()
    assert result.is_success
    assert result.value.exists()
    assert result.value.stat().st_size > 0
    assert result.value in backup.list_backups()


def test_restore_missing_file_fails(backup, tmp_path):
    result = backup.restore_backup(tmp_path / "does-not-exist.db")
    assert result.is_failure


def test_restore_from_created_backup_succeeds(backup):
    created = backup.create_backup()
    assert created.is_success
    assert backup.restore_backup(created.value).is_success
