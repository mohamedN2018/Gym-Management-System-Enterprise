"""Core kernel — the innermost architectural layer.

This package is intentionally **dependency-free** (no UI, no ORM, no I/O). It defines the
framework primitives every other layer builds on:

- :mod:`app.core.errors`     — typed error hierarchy (:class:`AppError`) and :class:`ErrorCode`
- :mod:`app.core.result`     — :class:`Result` / :class:`Error` value objects (railway flow)
- :mod:`app.core.constants`  — application identity and framework defaults
- :mod:`app.core.pagination` — :class:`PageRequest`, :class:`Page`, :class:`Sort`
- :mod:`app.core.events`     — in-process :class:`EventBus`
- :mod:`app.core.di`         — :class:`Container` (dependency injection)
- :mod:`app.core.base`       — abstract DTO / Repository / UnitOfWork / Service / Validator

Nothing here may import from ``app.database``, ``app.modules`` or any UI package.
"""
