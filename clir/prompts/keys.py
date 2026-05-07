"""Keyboard shortcuts for prompts."""

from typing import Callable, Any
from prompt_toolkit.key_binding import KeyBindings, EmergencyBreak
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding.key_processor import KeyPressEvent


# Common keyboard shortcuts
class Keys:
    """Key constants for common shortcuts."""

    # Control keys
    CTRL_C = Keys.ControlC
    CTRL_D = Keys.ControlD
    CTRL_Z = Keys.ControlZ
    CTRL_L = Keys.ControlL
    CTRL_R = Keys.ControlR
    CTRL_U = Keys.ControlU
    CTRL_K = Keys.ControlK
    CTRL_A = Keys.ControlA
    CTRL_E = Keys.ControlE

    # Navigation
    UP = Keys.Up
    DOWN = Keys.Down
    LEFT = Keys.Left
    RIGHT = Keys.Right
    HOME = Keys.Home
    END = Keys.End
    PAGE_UP = Keys.PageUp
    PAGE_DOWN = Keys.PageDown

    # Editing
    BACKSPACE = Keys.Backspace
    DELETE = Keys.Delete
    INSERT = Keys.Insert
    TAB = Keys.Tab
    ENTER = Keys.Enter
    ESCAPE = Keys.Escape


def create_keybindings(
    **shortcuts: tuple[str, Callable[[], Any]],
) -> KeyBindings:
    """Create key bindings from a dictionary.

    Args:
        **shortcuts: Key names mapped to handler functions.
                     Keys can be strings like 'c-a', 'c-c', 'up', 'down', etc.

    Returns:
        KeyBindings object

    Example:
        bindings = create_keybindings(
            ctl('c'): lambda: print('Ctrl+C pressed'),
            'up': lambda: move_cursor_up(),
            'ctrl-r': lambda: refresh(),
        )
    """
    bindings = KeyBindings()

    for key_spec, handler in shortcuts.items():
        _add_binding(bindings, key_spec, handler)

    return bindings


def _add_binding(
    bindings: KeyBindings,
    key_spec: str,
    handler: Callable[[], Any],
) -> None:
    """Add a single key binding."""
    # Parse key spec like "c-a" -> Ctrl+A, "up" -> Up, etc.
    keys = _parse_key_spec(key_spec)

    @bindings.add(*keys)
    def _(event: KeyPressEvent) -> None:
        handler()


def _parse_key_spec(key_spec: str) -> list[str]:
    """Parse a key specification string into a list of keys.

    Args:
        key_spec: Key specification like "c-a", "ctrl-c", "up", "escape"

    Returns:
        List of key identifiers
    """
    key_spec = key_spec.lower().strip()
    parts = []

    # Handle Ctrl combinations
    if key_spec.startswith("c-") or key_spec.startswith("ctrl-"):
        # Extract the key after ctrl/
        if key_spec.startswith("ctrl-"):
            key = key_spec[5:]
        else:
            key = key_spec[2:]

        # Map common key names
        key_map = {
            "a": "c-a",
            "b": "c-b",
            "c": "c-c",
            "d": "c-d",
            "e": "c-e",
            "f": "c-f",
            "g": "c-g",
            "h": "c-h",
            "i": "c-i",
            "j": "c-j",
            "k": "c-k",
            "l": "c-l",
            "m": "c-m",
            "n": "c-n",
            "o": "c-o",
            "p": "c-p",
            "q": "c-q",
            "r": "c-r",
            "s": "c-s",
            "t": "c-t",
            "u": "c-u",
            "v": "c-v",
            "w": "c-w",
            "x": "c-x",
            "y": "c-y",
            "z": "c-z",
            "[": "c-[",
            "\\": "c-\\",
            "]": "c-]",
            "^": "c-^",
            "_": "c-_",
        }
        parts.append(key_map.get(key, f"c-{key}"))
    else:
        # Single key
        key_map = {
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "enter": "enter",
            "escape": "escape",
            "esc": "escape",
            "tab": "tab",
            "backspace": "backspace",
            "delete": "delete",
            "home": "home",
            "end": "end",
            "pageup": "pageup",
            "pagedown": "pagedown",
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
        }
        parts.append(key_map.get(key_spec, key_spec))

    return parts


def ctl(key: str) -> str:
    """Shorthand for Ctrl+key.

    Args:
        key: Single character key

    Returns:
        Key specification string

    Example:
        bindings = create_keybindings(
            ctl('c'): abort,
            ctl('g'): cancel,
        )
    """
    return f"c-{key}"


def ctrl(key: str) -> str:
    """Alias for ctl()."""
    return f"ctrl-{key}"


__all__ = [
    "Keys",
    "create_keybindings",
    "ctl",
    "ctrl",
]