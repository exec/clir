"""Styled output functions using Rich with theme support and terminal capability detection."""

import os
import sys
from typing import Any

from rich.console import Console
from rich.theme import Theme

# Terminal capability detection
def _detect_terminal_capability() -> str:
    """Detect terminal color capability.

    Returns:
        'truecolor' - 24-bit colors (most modern terminals)
        '256' - 256 color mode
        'basic' - 16 standard colors
    """
    # Check COLORTERM env var (most reliable)
    colorterm = os.environ.get('COLORTERM', '')
    if colorterm == 'truecolor':
        return 'truecolor'

    # Check for 256 color
    term = os.environ.get('TERM', '')
    if '256' in term or colorterm == '256color':
        return '256'

    # Check with tput
    try:
        import subprocess
        colors = subprocess.check_output(['tput', 'colors'], stderr=subprocess.DEVNULL)
        colors = int(colors.decode().strip())
        if colors >= 256:
            return 'truecolor'
        elif colors >= 16:
            return '256'
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError):
        # OSError covers environments that lack subprocess support, e.g.
        # Pyodide/emscripten which raises OSError(138, "emscripten does
        # not support processes.").
        pass

    return 'basic'


# Color definitions for each capability tier
# Format: {theme_name: {capability: {style: color}}}
_THEME_COLORS = {
    "default": {
        "truecolor": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "dim"},
        "256": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "dim"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "dim"},
    },
    "dade": {
        "truecolor": {"success": "#00ff00 bold", "error": "#ff0000 bold", "warning": "#ffff00 bold", "info": "#00ffff", "debug": "#008800"},
        "256": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "green"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "green"},
    },
    "bubblegum": {
        "truecolor": {"success": "#ff69b4 bold", "error": "#ff1493 bold", "warning": "#ffb6c1 bold", "info": "#da70d6", "debug": "#ffb6c1"},
        "256": {"success": "magenta bold", "error": "red bold", "warning": "yellow bold", "info": "magenta", "debug": "magenta"},
        "basic": {"success": "magenta bold", "error": "red bold", "warning": "magenta bold", "info": "magenta", "debug": "magenta"},
    },
    "ocean": {
        "truecolor": {"success": "#00ced1 bold", "error": "#ff6b6b bold", "warning": "#ffd93d bold", "info": "#4ecdc4", "debug": "#95e1d3"},
        "256": {"success": "dark_cyan bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "cyan"},
        "basic": {"success": "cyan bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "cyan"},
    },
    "sunset": {
        "truecolor": {"success": "#fd9644 bold", "error": "#fc5c65 bold", "warning": "#fed330 bold", "info": "#be2edd", "debug": "#a55eea"},
        "256": {"success": "dark_orange bold", "error": "red bold", "warning": "yellow bold", "info": "magenta", "debug": "magenta"},
        "basic": {"success": "red bold", "error": "red bold", "warning": "yellow bold", "info": "magenta", "debug": "magenta"},
    },
    "monokai": {
        "truecolor": {"success": "#a6e22e bold", "error": "#f92672 bold", "warning": "#e6db74 bold", "info": "#66d9ef", "debug": "#75715e"},
        "256": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "white"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "white"},
    },
    "dracula": {
        "truecolor": {"success": "#50fa7b bold", "error": "#ff5555 bold", "warning": "#f1fa8c bold", "info": "#bd93f9", "debug": "#6272a4"},
        "256": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "magenta", "debug": "blue"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "magenta", "debug": "blue"},
    },
    "nord": {
        "truecolor": {"success": "#88c0d0 bold", "error": "#bf616a bold", "warning": "#ebcb8b bold", "info": "#81a1c1", "debug": "#5e81ac"},
        "256": {"success": "cyan bold", "error": "red bold", "warning": "yellow bold", "info": "blue", "debug": "blue"},
        "basic": {"success": "cyan bold", "error": "red bold", "warning": "yellow bold", "info": "blue", "debug": "blue"},
    },
    "gruvbox": {
        "truecolor": {"success": "#98971a bold", "error": "#cc241d bold", "warning": "#d79921 bold", "info": "#458588", "debug": "#928374"},
        "256": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "white"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "white"},
    },
    "one-dark": {
        "truecolor": {"success": "#98c379 bold", "error": "#e06c75 bold", "warning": "#e5c07b bold", "info": "#61afef", "debug": "#5c6370"},
        "256": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "blue", "debug": "white"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "blue", "debug": "white"},
    },
    "synthwave": {
        "truecolor": {"success": "#ff79c6 bold", "error": "#ff5555 bold", "warning": "#f1fa8c bold", "info": "#bd93f9", "debug": "#6272a4"},
        "256": {"success": "magenta bold", "error": "red bold", "warning": "yellow bold", "info": "magenta", "debug": "blue"},
        "basic": {"success": "magenta bold", "error": "red bold", "warning": "yellow bold", "info": "magenta", "debug": "blue"},
    },
    "matrix": {
        "truecolor": {"success": "#00ff00 bold", "error": "#ff0000 bold", "warning": "#ffff00 bold", "info": "#00ff00", "debug": "#003300"},
        "256": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "green", "debug": "green"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "green", "debug": "green"},
    },
    "pastel": {
        "truecolor": {"success": "#b8e994 bold", "error": "#ffaaa5 bold", "warning": "#ffd3a5 bold", "info": "#a8d8ea", "debug": "#c5e3f6"},
        "256": {"success": "green bold", "error": "light_red bold", "warning": "light_yellow bold", "info": "light_cyan", "debug": "white"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "cyan", "debug": "white"},
    },
    "high-contrast": {
        "truecolor": {"success": "#00ff00 bold reverse", "error": "#ff0000 bold reverse", "warning": "#ffff00 bold reverse", "info": "#00ffff bold", "debug": "#ffffff bold"},
        "256": {"success": "green bold reverse", "error": "red bold reverse", "warning": "yellow bold reverse", "info": "cyan bold", "debug": "white bold"},
        "basic": {"success": "green bold reverse", "error": "red bold reverse", "warning": "yellow bold reverse", "info": "cyan bold", "debug": "white bold"},
    },
    "material": {
        "truecolor": {"success": "#4caf50 bold", "error": "#f44336 bold", "warning": "#ff9800 bold", "info": "#2196f3", "debug": "#9e9e9e"},
        "256": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "blue", "debug": "white"},
        "basic": {"success": "green bold", "error": "red bold", "warning": "yellow bold", "info": "blue", "debug": "white"},
    },
    "catppuccin": {
        "truecolor": {"success": "#a6e3a1 bold", "error": "#f38ba8 bold", "warning": "#f9e2af bold", "info": "#89b4fa", "debug": "#6c7086"},
        "256": {"success": "green bold", "error": "magenta bold", "warning": "yellow bold", "info": "blue", "debug": "white"},
        "basic": {"success": "green bold", "error": "magenta bold", "warning": "yellow bold", "info": "blue", "debug": "white"},
    },
    # Examples theme - colorful mix inspired by various aesthetics
    "examples": {
        "truecolor": {"success": "#50fa7b bold", "error": "#ff79c6 bold", "warning": "#ffb86c bold", "info": "#8be9fd bold", "debug": "#6272a4"},
        "256": {"success": "green bold", "error": "magenta bold", "warning": "yellow bold", "info": "cyan bold", "debug": "blue"},
        "basic": {"success": "green bold", "error": "magenta bold", "warning": "yellow bold", "info": "cyan bold", "debug": "blue"},
    },
}

# Detect current terminal capability
TERMINAL_CAPABILITY = _detect_terminal_capability()

# Current state
_current_theme_name = "default"


def set_theme(name: str) -> None:
    """Set the active theme by name (automatically uses appropriate color tier).

    Args:
        name: Theme name (must exist in _THEME_COLORS)

    Raises:
        ValueError: If theme name doesn't exist
    """
    global _current_theme_name

    if name not in _THEME_COLORS:
        raise ValueError(f"Unknown theme: {name}. Available: {list(_THEME_COLORS.keys())}")

    _current_theme_name = name
    _apply_theme(name)


# Dark/Light theme recommendations
_DARK_THEMES = ["monokai", "dracula", "nord", "synthwave", "one-dark", "matrix", "gruvbox"]
_LIGHT_THEMES = ["default", "ocean", "sunset", "bubblegum", "pastel", "material", "catppuccin"]


def get_recommended_theme() -> str:
    """Get recommended theme based on terminal background.

    Returns:
        Theme name
    """
    scheme = detect_terminal_background()
    if scheme == "dark":
        return "monokai"
    return "default"


def auto_theme() -> None:
    """Automatically set theme based on terminal background."""
    theme = get_recommended_theme()
    set_theme(theme)


# Dark/Light theme recommendations
_DARK_THEMES = ["monokai", "dracula", "nord", "synthwave", "one-dark", "matrix", "gruvbox"]
_LIGHT_THEMES = ["default", "ocean", "sunset", "bubblegum", "pastel", "material", "catppuccin"]


def get_recommended_theme() -> str:
    """Get recommended theme based on terminal background.

    Returns:
        Theme name
    """
    scheme = detect_terminal_background()
    if scheme == "dark":
        return "monokai"
    return "default"


def auto_theme() -> None:
    """Automatically set theme based on terminal background."""
    set_theme(get_recommended_theme())


def _apply_theme(name: str) -> None:
    """Apply a theme based on terminal capability.

    Rebuilds both the stdout and stderr consoles so they always share a theme.
    """
    global console, _stderr_console

    theme_colors = _THEME_COLORS.get(name, _THEME_COLORS["default"])
    colors = theme_colors.get(TERMINAL_CAPABILITY, theme_colors["basic"])

    _custom_theme = Theme(colors)
    console = Console(theme=_custom_theme)
    _stderr_console = Console(theme=_custom_theme, stderr=True)


def get_theme() -> str:
    """Get the current theme name."""
    return _current_theme_name


def get_terminal_capability() -> str:
    """Get the detected terminal color capability."""
    return TERMINAL_CAPABILITY


def detect_terminal_background() -> str:
    """Detect terminal background color (dark or light).

    Returns:
        'dark' or 'light'
    """
    # Check for explicit environment variable
    bg = os.environ.get("CLIR_THEME", "").lower()
    if bg in ("dark", "light"):
        return bg

    # Check VS Code setting
    vscode = os.environ.get("VSCODE_TERMINAL_BACKGROUND", "").lower()
    if vscode in ("dark", "light"):
        return vscode

    # Try to detect from ANSI escape codes
    try:
        import subprocess
        # Check iTerm2
        result = subprocess.run(
            ["osascript", "-e", 'tell app "Terminal" to get background color of front window'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            # Parse RGB values - dark terminals have lower values
            # This is a simplified check
            return "dark"  # macOS Terminal typically dark
    except (subprocess.SubprocessError, FileNotFoundError, TimeoutError):
        pass

    # Check for common dark terminal env vars
    if os.environ.get("TERM_PROGRAM") in ("iTerm.app", "vscode"):
        return "dark"

    # Check for dark color scheme indicators
    if "dark" in os.environ.get("COLORFGBG", "").lower():
        return "dark"

    # Default to dark (most common for devs)
    return "dark"


def auto_set_theme() -> None:
    """Automatically set theme based on terminal background."""
    bg = detect_terminal_background()

    if bg == "dark":
        # Use themes that work well on dark backgrounds
        dark_themes = ["monokai", "dracula", "nord", "one-dark", "synthwave"]
        set_theme("dracula")
    else:
        # Use themes that work well on light backgrounds
        light_themes = ["default", "material", "catppuccin", "ocean", "pastel"]
        set_theme("default")


def get_available_themes() -> list[str]:
    """Get list of available theme names."""
    return list(_THEME_COLORS.keys())


def get_console() -> Console:
    """Get the current console instance.

    Always call this instead of importing ``console`` directly — the instance
    is replaced when :func:`set_theme` is called, so a stale import-time
    reference will miss subsequent theme changes.
    """
    return console


def get_stderr_console() -> Console:
    """Get the current stderr console instance.

    Like get_console(), always call this instead of importing _stderr_console
    directly — the instance is replaced when set_theme is called.
    """
    return _stderr_console


# Initialize with default theme
_apply_theme("default")


def echo(*objects: object, sep: str = " ", end: str = "\n") -> None:
    """Print styled output. Always shown — user's escape hatch."""
    console.print(*objects, sep=sep, end=end)


def _styled(tag: str, objects: tuple[object, ...], sep: str) -> str:
    """Wrap joined objects in inline rich markup for the given style tag.

    Inline markup (vs. the style= kwarg) works in Consoles without a theme —
    rich silently falls back to plain text when the named style is undefined.
    """
    return f"[{tag}]{sep.join(str(o) for o in objects)}[/{tag}]"


def success(*objects: object, sep: str = " ") -> None:
    """Print success message to stdout. Suppressed by --quiet."""
    from clir.runtime import get_verbosity
    if get_verbosity().quiet:
        return
    console.print(_styled("success", objects, sep))


def info(*objects: object, sep: str = " ") -> None:
    """Print info message to stdout. Suppressed by --quiet."""
    from clir.runtime import get_verbosity
    if get_verbosity().quiet:
        return
    console.print(_styled("info", objects, sep))


def warning(*objects: object, sep: str = " ") -> None:
    """Print warning message to stderr. Suppressed by --quiet."""
    from clir.runtime import get_verbosity
    if get_verbosity().quiet:
        return
    _stderr_console.print(_styled("warning", objects, sep))


def error(*objects: object, sep: str = " ") -> None:
    """Print error message to stderr. Always shown."""
    _stderr_console.print(_styled("error", objects, sep))


def debug(*objects: object, sep: str = " ") -> None:
    """Print debug message to stderr. Only shown when --debug is set."""
    from clir.runtime import get_verbosity
    if not get_verbosity().debug:
        return
    _stderr_console.print(_styled("debug", objects, sep))


def json(data: Any, indent: int = 2, sort_keys: bool = False) -> None:
    """Pretty print JSON data.

    Args:
        data: Data to print as JSON
        indent: Indentation spaces
        sort_keys: Sort dictionary keys
    """
    import json
    from rich.json import JSON as RichJSON

    json_str = json.dumps(data, indent=indent, sort_keys=sort_keys)
    rich_json = RichJSON(json_str)
    console.print(rich_json)


def print_json(data: Any, pretty: bool = True) -> None:
    """Print data as JSON.

    Args:
        data: Data to print
        pretty: Use pretty printing
    """
    import json

    if pretty:
        console.print(json.dumps(data, indent=2))
    else:
        console.print(json.dumps(data))


# Backwards compatibility
THEMES = _THEME_COLORS
