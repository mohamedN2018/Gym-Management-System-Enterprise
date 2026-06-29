"""Infrastructure composition.

Hosts the application's composition root — :func:`~app.infrastructure.bootstrap.bootstrap` —
which constructs and wires every foundation service into a :class:`~app.core.di.Container`.
This is the one place that knows how the concrete pieces fit together; everything else depends
on abstractions.
"""

from app.infrastructure.bootstrap import ApplicationContext, bootstrap

__all__ = ["ApplicationContext", "bootstrap"]
