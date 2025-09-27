# measurekit/context.py
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from measurekit.system import UnitSystem

# Create a context variable to hold the active system.
# It has no default; the default is handled by get_active_system().
_active_system: ContextVar[UnitSystem] = ContextVar("active_system")


def get_active_system() -> UnitSystem:
    """Returns the currently active unit system from the context.

    If no system is set in the context, it falls back to the global
    default_system.
    """
    from measurekit import default_system

    return _active_system.get(default_system)


@contextmanager
def system_context(system: UnitSystem) -> Iterator[None]:
    """A context manager to temporarily set the active unit system.

    Examples:
        >>> import measurekit as mk
        >>> from measurekit.context import system_context
        # Create a new system or use an existing one
        >>> with system_context(my_other_system):
        ...     # Code inside this block will use my_other_system by default
        ...     q = 5 * mk.get_unit("m")  # q will belong to my_other_system
    """
    token = _active_system.set(system)
    try:
        yield
    finally:
        _active_system.reset(token)
