"""Member management service — create, query and soft-delete members."""

from __future__ import annotations

from collections.abc import Callable

from app.core.base.service import BaseService
from app.core.errors import ConflictError
from app.core.events import Event, EventBus
from app.core.pagination import Page, PageRequest
from app.core.result import Result
from app.database.unit_of_work import SqlAlchemyUnitOfWork
from app.logs.logging_service import LoggingService
from app.modules.members.dtos import (
    CreateMemberRequest,
    MemberDTO,
    UpdateMemberRequest,
    to_member_dto,
)
from app.modules.members.events import MemberEvents
from app.modules.members.models.member import Member
from app.modules.members.repositories import MemberRepository
from app.modules.members.validators import CreateMemberValidator

UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]

#: Membership numbers are generated as this prefix + a zero-padded sequence.
_MEMBERSHIP_PREFIX = "M"
_MEMBERSHIP_PAD = 5


class MemberService(BaseService):
    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        events: EventBus | None = None,
        logging: LoggingService | None = None,
    ) -> None:
        super().__init__(
            logger=logging.get_logger(__name__) if logging else None,
            events=events,
        )
        self._uow_factory = uow_factory
        self._logging = logging
        self._validator = CreateMemberValidator()

    def create_member(
        self, request: CreateMemberRequest, *, created_by: int | None = None
    ) -> Result[MemberDTO]:
        return self._guard(
            lambda: self._create_member(request, created_by), message="Could not create member"
        )

    def _create_member(self, request: CreateMemberRequest, created_by: int | None) -> MemberDTO:
        self._validator.validate_and_raise(request)
        with self._uow_factory() as uow:
            repo = MemberRepository(uow.session)
            number = (request.membership_number or "").strip() or self._next_number(repo)
            if repo.find_by_membership_number(number) is not None:
                raise ConflictError(
                    "Membership number already exists.",
                    details={"field": "membership_number", "value": number},
                )
            member = Member(
                membership_number=number,
                first_name=request.first_name.strip(),
                last_name=(request.last_name or None),
                phone=(request.phone or None),
                email=(request.email or None),
                national_id=(request.national_id or None),
                gender=(request.gender or None),
                birth_date=request.birth_date,
                address=(request.address or None),
                notes=(request.notes or None),
                created_by=created_by,
            )
            repo.add(member)
            dto = to_member_dto(member)
            uow.commit()

        if self._logging:
            self._logging.audit(
                action="create",
                module="members",
                result="success",
                user=created_by,
                new_value={"membership_number": dto.membership_number, "id": dto.id},
            )
        self._publish(
            Event(MemberEvents.CREATED, {"member_id": dto.id, "number": dto.membership_number})
        )
        return dto

    def update_member(
        self, member_id: int, request: UpdateMemberRequest, *, updated_by: int | None = None
    ) -> Result[MemberDTO]:
        return self._guard(
            lambda: self._update_member(member_id, request, updated_by),
            message="Could not update member",
        )

    def _update_member(
        self, member_id: int, request: UpdateMemberRequest, updated_by: int | None
    ) -> MemberDTO:
        self._validator.validate_and_raise(request)
        with self._uow_factory() as uow:
            repo = MemberRepository(uow.session)
            member = repo.get_or_raise(member_id)
            new_national_id = (request.national_id or "").strip() or None
            if new_national_id and new_national_id != member.national_id:
                clash = repo.find_one(national_id=new_national_id)
                if clash is not None and clash.id != member.id:
                    raise ConflictError(
                        "National ID already exists.",
                        details={"field": "national_id", "value": new_national_id},
                    )
            member.first_name = request.first_name.strip()
            member.last_name = (request.last_name or "").strip() or None
            member.phone = (request.phone or "").strip() or None
            member.email = (request.email or "").strip() or None
            member.national_id = new_national_id
            member.gender = request.gender or None
            member.birth_date = request.birth_date
            member.address = (request.address or "").strip() or None
            member.notes = (request.notes or "").strip() or None
            member.updated_by = updated_by
            repo.update(member)
            dto = to_member_dto(member)
            uow.commit()

        if self._logging:
            self._logging.audit(
                action="update",
                module="members",
                result="success",
                user=updated_by,
                new_value={"membership_number": dto.membership_number, "id": dto.id},
            )
        self._publish(
            Event(MemberEvents.UPDATED, {"member_id": dto.id, "number": dto.membership_number})
        )
        return dto

    def get_by_membership_number(self, membership_number: str) -> Result[MemberDTO | None]:
        def _get() -> MemberDTO | None:
            with self._uow_factory() as uow:
                member = MemberRepository(uow.session).find_by_membership_number(
                    membership_number.strip()
                )
                return to_member_dto(member) if member is not None else None

        return self._guard(_get, message="Could not load member")

    def get_member(self, member_id: int) -> Result[MemberDTO]:
        def _get() -> MemberDTO:
            with self._uow_factory() as uow:
                member = MemberRepository(uow.session).get_or_raise(member_id)
                return to_member_dto(member)

        return self._guard(_get, message="Could not load member")

    def list_members(self, request: PageRequest) -> Result[Page[MemberDTO]]:
        def _list() -> Page[MemberDTO]:
            with self._uow_factory() as uow:
                page = MemberRepository(uow.session).list(request)
                items = [to_member_dto(member) for member in page.items]
                return Page(items=items, total=page.total, page=page.page, size=page.size)

        return self._guard(_list, message="Could not list members")

    def delete_member(self, member_id: int, *, deleted_by: int | None = None) -> Result[None]:
        def _delete() -> None:
            with self._uow_factory() as uow:
                repo = MemberRepository(uow.session)
                member = repo.get_or_raise(member_id)
                repo.soft_delete(member, by=deleted_by)
                uow.commit()
            self._publish(Event(MemberEvents.DELETED, {"member_id": member_id}))

        return self._guard(_delete, message="Could not delete member")

    def _next_number(self, repo: MemberRepository) -> str:
        sequence = repo.count(include_deleted=True) + 1
        return f"{_MEMBERSHIP_PREFIX}{sequence:0{_MEMBERSHIP_PAD}d}"
