"""Minimal, explicit dependency-injection container.

Supports constructor injection without magic: register concrete instances or factories
(keyed by a type or a string token) and resolve them. Factories receive the container so they
can resolve their own dependencies. This is the single composition seam that keeps services
free of hardwired construction (Part 2: *Dependency Injection*), while staying KISS/YAGNI —
no autowiring reflection, no global state.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar, overload

from app.core.errors import ConfigurationError

T = TypeVar("T")

#: A registration key: either a type (preferred) or a string token.
Key = type | str
#: A factory builds an instance given the container (for resolving dependencies).
Factory = Callable[["Container"], object]


class Container:
    """Thread-safe service registry with singleton and transient lifetimes."""

    def __init__(self) -> None:
        self._instances: dict[Key, object] = {}
        self._factories: dict[Key, Factory] = {}
        self._singletons: set[Key] = set()
        self._singleton_cache: dict[Key, object] = {}
        self._lock = threading.RLock()

    # --- registration -----------------------------------------------------
    def register_instance(self, key: Key, instance: object) -> None:
        """Register an already-constructed instance (always singleton)."""
        with self._lock:
            self._instances[key] = instance

    def register_factory(self, key: Key, factory: Factory, *, singleton: bool = True) -> None:
        """Register a factory. Singleton factories are invoked at most once and cached."""
        with self._lock:
            self._factories[key] = factory
            if singleton:
                self._singletons.add(key)
            else:
                self._singletons.discard(key)
            self._singleton_cache.pop(key, None)

    # --- resolution -------------------------------------------------------
    @overload
    def resolve(self, key: type[T]) -> T: ...
    @overload
    def resolve(self, key: str) -> object: ...

    def resolve(self, key: Key) -> object:
        """Return the instance for ``key``, constructing it via its factory if needed."""
        with self._lock:
            if key in self._instances:
                return self._instances[key]
            if key in self._singleton_cache:
                return self._singleton_cache[key]
            factory = self._factories.get(key)
            if factory is None:
                raise ConfigurationError(
                    f"No registration for dependency: {_key_name(key)}",
                    details={"key": _key_name(key)},
                )
            is_singleton = key in self._singletons
            # Construct outside the dict mutations but still under the lock so concurrent
            # resolves of the same singleton return the same instance.
            instance = factory(self)
            if is_singleton:
                self._singleton_cache[key] = instance
            return instance

    def has(self, key: Key) -> bool:
        with self._lock:
            return key in self._instances or key in self._factories

    def clear(self) -> None:
        """Drop all registrations (used by tests)."""
        with self._lock:
            self._instances.clear()
            self._factories.clear()
            self._singletons.clear()
            self._singleton_cache.clear()


def _key_name(key: Key) -> str:
    return key.__name__ if isinstance(key, type) else str(key)
