"""Command hooks for pre/post execution."""

from __future__ import annotations

from typing import Any, Callable, Awaitable
from functools import wraps

# Type for hook functions
HookFunc = Callable[..., Awaitable[Any] | None]


class Hooks:
    """Manage command hooks (before/after)."""

    def __init__(self):
        self._before: list[tuple[str, HookFunc]] = []
        self._after: list[tuple[str, HookFunc]] = []

    def before(self, command_name: str, func: HookFunc) -> None:
        """Register a before hook for a command.

        Args:
            command_name: Command to hook
            func: Async function to run before command
        """
        self._before.append((command_name, func))

    def after(self, command_name: str, func: HookFunc) -> None:
        """Register an after hook for a command.

        Args:
            command_name: Command to hook
            func: Async function to run after command
        """
        self._after.append((command_name, func))

    def get_before(self, command_name: str) -> list[HookFunc]:
        """Get before hooks for a command."""
        return [f for cmd, f in self._before if cmd == command_name or cmd == "*"]

    def get_after(self, command_name: str) -> list[HookFunc]:
        """Get after hooks for a command."""
        return [f for cmd, f in self._after if cmd == command_name or cmd == "*"]

    def clear(self, command_name: str | None = None) -> None:
        """Clear hooks for a command or all."""
        if command_name is None:
            self._before.clear()
            self._after.clear()
        else:
            self._before = [(c, f) for c, f in self._before if c != command_name]
            self._after = [(c, f) for c, f in self._after if c != command_name]


def before(command_name: str = "*") -> Callable[[HookFunc], HookFunc]:
    """Decorator to register a before hook.

    Args:
        command_name: Command to hook (default: all commands)

    Example:
        @before("greet")
        async def log_greeting(ctx):
            print(f"About to greet: {ctx.args}")
    """
    def decorator(func: HookFunc) -> HookFunc:
        # Store for later registration with app
        if not hasattr(func, "_clir_hooks"):
            func._clir_hooks = []
        func._clir_hooks.append(("before", command_name))
        return func
    return decorator


def after(command_name: str = "*") -> Callable[[HookFunc], HookFunc]:
    """Decorator to register an after hook.

    Args:
        command_name: Command to hook (default: all commands)

    Example:
        @after("greet")
        async def log_greeting(ctx):
            print(f"Greeted successfully!")
    """
    def decorator(func: HookFunc) -> HookFunc:
        if not hasattr(func, "_clir_hooks"):
            func._clir_hooks = []
        func._clir_hooks.append(("after", command_name))
        return func
    return decorator


__all__ = ["Hooks", "before", "after"]