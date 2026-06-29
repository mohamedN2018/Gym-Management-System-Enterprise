"""Shared pytest fixtures.

Each test gets an isolated SQLite database under a unique ``tmp_path`` so tests never share
state and run in parallel safely.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from app.database.base import Base
from app.database.engine import create_engine_and_session_factory
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure import ApplicationContext, bootstrap
from app.settings import AppConfig, AppPaths, load_config
from sqlalchemy.orm import Session, sessionmaker

from tests.support.sample_models import Widget, WidgetRepository


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return load_config(environment="test", data_dir=str(tmp_path))


@pytest.fixture
def app_paths(tmp_path: Path) -> AppPaths:
    return AppPaths.resolve(tmp_path).ensure()


@pytest.fixture
def session_factory(app_config: AppConfig, app_paths: AppPaths) -> Iterator[sessionmaker[Session]]:
    engine, factory = create_engine_and_session_factory(app_config, app_paths)
    Base.metadata.create_all(engine, tables=[Widget.__table__])
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def make_uow(session_factory: sessionmaker[Session]) -> Callable[[], SqlAlchemyUnitOfWork]:
    return lambda: SqlAlchemyUnitOfWork(session_factory)


@pytest.fixture
def widget_repo_factory() -> type[WidgetRepository]:
    return WidgetRepository


@pytest.fixture
def security_context(tmp_path: Path) -> Iterator[ApplicationContext]:
    """A fully bootstrapped context with the security schema created and RBAC seeded."""
    from app.modules.security.setup import initialize_security

    context = bootstrap(load_config(environment="test", data_dir=str(tmp_path)))
    initialize_security(context)
    try:
        yield context
    finally:
        context.dispose()


@pytest.fixture
def gym_context(tmp_path: Path) -> Iterator[ApplicationContext]:
    """A context with all business modules wired (security, members, membership, attendance)."""
    from app.modules.attendance.setup import register_attendance_services
    from app.modules.employees.setup import register_employee_services
    from app.modules.inventory.setup import initialize_inventory
    from app.modules.members.setup import register_members_services
    from app.modules.membership.setup import initialize_membership
    from app.modules.notifications.setup import register_notification_services
    from app.modules.payments.setup import initialize_payments
    from app.modules.reports.setup import register_report_services
    from app.modules.security.setup import initialize_security
    from app.modules.settings.setup import register_settings_services
    from app.modules.trainers.setup import register_trainer_services

    context = bootstrap(load_config(environment="test", data_dir=str(tmp_path)))
    initialize_security(context)
    register_members_services(context.container)
    initialize_membership(context)
    register_attendance_services(context.container)
    initialize_payments(context)
    register_trainer_services(context.container)
    register_settings_services(context.container)
    initialize_inventory(context)
    register_report_services(context.container)
    register_employee_services(context.container)
    register_notification_services(context.container)
    try:
        yield context
    finally:
        context.dispose()
