"""Employee repository (persistence only)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.repository import SqlAlchemyRepository
from app.modules.employees.models.employee import Employee


class EmployeeRepository(SqlAlchemyRepository[Employee]):
    searchable_fields = ("code", "first_name", "last_name", "phone", "position", "department")

    def __init__(self, session: Session) -> None:
        super().__init__(Employee, session)
