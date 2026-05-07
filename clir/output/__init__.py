"""Output module for rich terminal output."""

from rich.console import Console
from clir.output.style import (
    success, error, warning, info, debug, echo,
    set_theme, get_theme, get_available_themes, get_terminal_capability,
    get_console, get_stderr_console, THEMES, json, print_json,
)
from clir.output.table import Table
from clir.output.progress import Progress
from clir.output.panel import Panel
from clir.output.spinner import Spinner
from clir.output.tree import Tree
from clir.output.select_table import SelectTable
from clir.output.markdown import Markdown, render_markdown

__all__ = [
    "Console",
    "echo",
    "success",
    "error",
    "warning",
    "info",
    "debug",
    "json",
    "print_json",
    "Table",
    "Progress",
    "Panel",
    "Spinner",
    "Tree",
    "SelectTable",
    "Markdown",
    "render_markdown",
    # Theme functions
    "set_theme",
    "get_theme",
    "get_available_themes",
    "get_terminal_capability",
    "get_console",
    "get_stderr_console",
    "THEMES",
]