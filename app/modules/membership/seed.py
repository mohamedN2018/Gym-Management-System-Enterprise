"""Idempotent seeding of default membership plans."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.modules.membership.models.plan import MembershipPlan
from app.modules.membership.repositories import PlanRepository

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


@dataclass(frozen=True, slots=True)
class _PlanSeed:
    code: str
    name: str
    price: Decimal
    duration_days: int


_DEFAULT_PLANS: tuple[_PlanSeed, ...] = (
    _PlanSeed("MONTHLY", "Monthly", Decimal("300.00"), 30),
    _PlanSeed("QUARTERLY", "Quarterly", Decimal("800.00"), 90),
    _PlanSeed("YEARLY", "Yearly", Decimal("2800.00"), 365),
)


def seed_default_plans(uow_factory: UnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        repo = PlanRepository(uow.session)
        for spec in _DEFAULT_PLANS:
            if repo.find_by_code(spec.code) is None:
                repo.add(
                    MembershipPlan(
                        code=spec.code,
                        name=spec.name,
                        price=spec.price,
                        duration_days=spec.duration_days,
                    )
                )
        uow.commit()
