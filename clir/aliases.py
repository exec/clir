"""Command aliases for CLI applications."""

from __future__ import annotations

from typing import Any, Callable


class AliasManager:
    """Manage command aliases for CLI apps."""

    def __init__(self):
        self._aliases: dict[str, str] = {}  # alias -> command
        self._reverse: dict[str, list[str]] = {}  # command -> list of aliases

    def add(self, alias: str, command: str) -> None:
        """Add an alias for a command.

        Args:
            alias: The alias name
            command: The full command path (e.g., "config set")
        """
        self._aliases[alias] = command
        if command not in self._reverse:
            self._reverse[command] = []
        if alias not in self._reverse[command]:
            self._reverse[command].append(alias)

    def remove(self, alias: str) -> bool:
        """Remove an alias.

        Args:
            alias: The alias to remove

        Returns:
            True if alias was removed, False if not found
        """
        if alias not in self._aliases:
            return False
        command = self._aliases.pop(alias)
        if command in self._reverse and alias in self._reverse[command]:
            self._reverse[command].remove(alias)
        return True

    def resolve(self, name: str) -> str | None:
        """Resolve an alias to its command.

        Args:
            name: Command or alias name

        Returns:
            The resolved command name, or None if not found
        """
        return self._aliases.get(name)

    def get_aliases(self, command: str | None = None) -> dict[str, str] | list[str]:
        """Get all aliases or aliases for a specific command.

        Args:
            command: If provided, get aliases for this command only

        Returns:
            Dict of all aliases or list of aliases for command
        """
        if command is None:
            return dict(self._aliases)
        return self._reverse.get(command, [])

    def is_alias(self, name: str) -> bool:
        """Check if a name is an alias.

        Args:
            name: Name to check

        Returns:
            True if name is an alias
        """
        return name in self._aliases


def alias(
    name: str | list[str],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to define aliases for a command function.

    Args:
        name: Single alias or list of aliases

    Returns:
        Decorator function

    Examples:
        @alias("ls")
        @command()
        def list_items(): ...

        @alias(["hi", "greet"])
        @command()
        def hello(): ...
    """
    aliases = name if isinstance(name, list) else [name]

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store aliases on the function for later retrieval
        if not hasattr(func, "_clir_aliases"):
            func._clir_aliases = []
        func._clir_aliases.extend(aliases)
        return func

    return decorator


__all__ = ["AliasManager", "alias"]