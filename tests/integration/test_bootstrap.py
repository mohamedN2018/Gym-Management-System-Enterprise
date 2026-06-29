import pytest
from app.core.events import Event, EventBus
from app.infrastructure import bootstrap
from app.infrastructure.bootstrap import UOW_FACTORY_KEY, ApplicationContext
from app.localization.localization_service import LocalizationService
from app.security.encryption import EncryptionService
from app.security.password_hasher import PasswordHasher
from app.settings import load_config

pytestmark = pytest.mark.integration


def _context(tmp_path):
    return bootstrap(load_config(environment="test", data_dir=str(tmp_path)))


def test_bootstrap_wires_everything(tmp_path):
    ctx = _context(tmp_path)
    try:
        assert ctx.verify_database() is True
        assert ctx.paths.data_dir.exists()
        assert ctx.paths.encryption_key_file.exists()

        assert isinstance(ctx.container.resolve(PasswordHasher), PasswordHasher)
        assert isinstance(ctx.container.resolve(EncryptionService), EncryptionService)
        assert isinstance(ctx.container.resolve(EventBus), EventBus)
        assert isinstance(ctx.container.resolve(LocalizationService), LocalizationService)
        assert ctx.localization is ctx.container.resolve(LocalizationService)
        assert ctx.container.resolve(ApplicationContext) is ctx

        uow_factory = ctx.container.resolve(UOW_FACTORY_KEY)
        with uow_factory() as uow:
            assert uow.session is not None
    finally:
        ctx.dispose()


def test_event_handler_error_does_not_propagate(tmp_path):
    ctx = _context(tmp_path)
    try:

        def failing(_e: Event) -> None:
            raise RuntimeError("boom")

        ctx.events.subscribe("x", failing)
        # The error sink is wired to logging; publishing must not raise.
        ctx.events.publish(Event("x"))
    finally:
        ctx.dispose()
