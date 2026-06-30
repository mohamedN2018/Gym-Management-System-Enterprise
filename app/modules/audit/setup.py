"""Audit module wiring."""

from __future__ import annotations

from app.core.di import Container
from app.logs.logging_service import LoggingService
from app.modules.audit.services import AuditService
from app.settings.paths import AppPaths


def register_audit_services(container: Container) -> None:
    container.register_factory(
        AuditService,
        lambda c: AuditService(paths=c.resolve(AppPaths), logging=c.resolve(LoggingService)),
    )
