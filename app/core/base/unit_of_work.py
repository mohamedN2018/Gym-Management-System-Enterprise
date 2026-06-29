"""Unit-of-Work interface — the transactional boundary.

A service does its work inside a single unit of work so that a multi-step operation either
fully commits or fully rolls back (Part 1: *use transactions*; Part 2: *services own
transactions*). The concrete SQLAlchemy implementation lives in
:mod:`app.database.unit_of_work`.

Typical usage::

    with uow:
        member = uow.members.add(entity)
        uow.commit()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType


class IUnitOfWork(ABC):
    """Context-managed transactional scope.

    On ``__exit__`` without an explicit :meth:`commit`, the implementation must roll back, so
    an un-committed (or failed) block never leaves a partial write behind.
    """

    @abstractmethod
    def __enter__(self) -> IUnitOfWork: ...

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool: ...

    @abstractmethod
    def commit(self) -> None:
        """Flush and commit all staged changes."""

    @abstractmethod
    def rollback(self) -> None:
        """Discard all staged changes."""
