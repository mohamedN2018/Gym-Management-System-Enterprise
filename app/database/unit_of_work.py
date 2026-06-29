"""SQLAlchemy Unit of Work.

Wraps a single ``Session`` in a transactional scope. Per the :class:`IUnitOfWork` contract, an
``__exit__`` without an explicit :meth:`commit` rolls back, so no block ever leaves a partial
write behind. Framework/ORM exceptions are translated to the typed :class:`AppError` hierarchy
so business and UI layers never see raw SQLAlchemy errors.
"""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app.core.base.unit_of_work import IUnitOfWork
from app.core.errors import ConcurrencyError, ConflictError, DatabaseError, InfrastructureError


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Transactional scope backed by a SQLAlchemy session."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._committed = False

    @property
    def session(self) -> Session:
        """The active session. Valid only inside a ``with`` block."""
        if self._session is None:
            raise InfrastructureError("Unit of work is not active; use it as a context manager.")
        return self._session

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            if self._session is not None:
                self._session.close()
                self._session = None
        # Do not suppress exceptions raised inside the block.
        return False

    def commit(self) -> None:
        try:
            self.session.commit()
            self._committed = True
        except StaleDataError as exc:
            self.rollback()
            raise ConcurrencyError(
                "The record was modified by someone else. Reload and try again.",
                cause=exc,
            ) from exc
        except IntegrityError as exc:
            self.rollback()
            raise ConflictError(
                "The operation violates a uniqueness or integrity constraint.",
                details={"reason": _sanitize(exc)},
                cause=exc,
            ) from exc
        except SQLAlchemyError as exc:
            self.rollback()
            raise DatabaseError(
                "A database error occurred while saving changes.", cause=exc
            ) from exc

    def rollback(self) -> None:
        if self._session is not None:
            self._session.rollback()


#: Callable that produces a fresh unit of work; injected into services via DI.
UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


def _sanitize(exc: SQLAlchemyError) -> str:
    """Short, UI-safe reason extracted from a DB exception (no SQL, no secrets)."""
    origin = getattr(exc, "orig", None)
    return str(origin) if origin is not None else exc.__class__.__name__
