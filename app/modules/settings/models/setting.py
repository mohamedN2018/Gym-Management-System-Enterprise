"""Setting entity — one persisted key/value application setting."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Entity


class SettingKeys:
    COMPANY_NAME = "company.name"
    COMPANY_CURRENCY = "company.currency"
    COMPANY_PHONE = "company.phone"


class Setting(Entity):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
