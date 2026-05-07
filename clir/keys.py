"""Keyboard shortcuts for CLI interactions."""

from __future__ import annotations

from typing import Any, Callable
from prompt_toolkit.key_binding import KeyBindings


class KeyboardShortcuts:
    """Manage keyboard shortcuts for CLI apps."""

    # Default shortcuts
    DEFAULT_SHORTCUTS = {
        "ctrl-c": "cancel",
        "ctrl-d": "quit",
        "ctrl-z": "suspend",
        "ctrl-l": "clear",
        "ctrl-a": "beginning-of-line",
        "ctrl-e": "end-of-line",
        "ctrl-k": "kill-line",
        "ctrl-u": "unix-line-discard",
        "ctrl-w": "unix-word-rubout",
    }

    def __init__(self):
        self._bindings: KeyBindings = KeyBindings()
        self._callbacks: dict[str, Callable] = {}

    def add(
        self,
        key: str,
        handler: Callable,
        description: str | None = None,
    ) -> None:
        """Add a keyboard shortcut.

        Args:
            key: Key binding (e.g., "ctrl-s", "f1")
            handler: Function to call when pressed
            description: Optional description
        """
        # Convert "ctrl-x" format to prompt_toolkit format
        keys = self._parse_key(key)
        self._bindings.add(keys)(handler)
        self._callbacks[key] = handler

    def _parse_key(self, key: str) -> tuple:
        """Parse key string to prompt_toolkit key tuple."""
        key_lower = key.lower()

        # Handle common shortcuts
        key_map = {
            "ctrl-c": "c-c",
            "ctrl-d": "c-d",
            "ctrl-s": "c-s",
            "ctrl-z": "c-z",
            "ctrl-a": "c-a",
            "ctrl-e": "c-e",
            "ctrl-k": "c-k",
            "ctrl-u": "c-u",
            "ctrl-w": "c-w",
            "ctrl-l": "c-l",
            "f1": "f1",
            "f2": "f2",
            "f3": "f3",
            "f4": "f4",
            "f5": "f5",
            "f6": "f6",
            "f7": "f7",
            "f8": "f8",
            "f9": "f9",
            "f10": "f10",
            "f11": "f11",
            "f12": "f12",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "enter": "enter",
            "tab": "tab",
            "esc": "escape",
            "backspace": "backspace",
            "delete": "delete",
        }

        return (key_map.get(key_lower, key_lower),)

    def get_bindings(self) -> KeyBindings:
        """Get the key bindings."""
        return self._bindings

    def remove(self, key: str) -> bool:
        """Remove a keyboard shortcut."""
        if key in self._callbacks:
            del self._callbacks[key]
            return True
        return False

    def list_shortcuts(self) -> list[tuple[str, Callable]]:
        """List all registered shortcuts."""
        return list(self._callbacks.items())


def create_shortcut(
    key: str,
    handler: Callable,
) -> tuple[tuple, Callable]:
    """Create a key binding tuple.

    Args:
        key: Key string (e.g., "ctrl-s")
        handler: Handler function

    Returns:
        Tuple of (key_tuple, handler)
    """
    ks = KeyboardShortcuts()
    return (ks._parse_key(key), handler)


__all__ = ["KeyboardShortcuts", "create_shortcut"]