"""Context object passed to CLI commands."""

from __future__ import annotations

from typing import Any


class Context:
    """Context object passed to CLI commands."""

    def __init__(
        self,
        command_name: str,
        args: dict[str, Any],
        parent: Context | None = None,
    ):
        self.command_name = command_name
        self.args = args
        self.parent = parent

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from context args."""
        return self.args.get(key, default)

    def __repr__(self) -> str:
        return f"Context({self.command_name})"
