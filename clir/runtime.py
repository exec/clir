"""Runtime state for clir applications.

Holds verbosity state in a ContextVar so it is async-safe and per-task,
allowing two concurrent ClirApp invocations in the same process to maintain
independent verbosity without stomping each other.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class Verbosity:
    """Verbosity flags for output gating."""

    quiet: bool = False
    verbose: bool = False
    debug: bool = False


_verbosity: ContextVar[Verbosity] = ContextVar(
    "clir_verbosity", default=Verbosity()
)


def get_verbosity() -> Verbosity:
    """Return the current verbosity for this context."""
    return _verbosity.get()


def set_verbosity(v: Verbosity) -> None:
    """Set the verbosity for the current context.

    Called once by ClirApp.run after parsing global flags. May also be called
    directly by library users who want to gate output without going through
    ClirApp.
    """
    _verbosity.set(v)
