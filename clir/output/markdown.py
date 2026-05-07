"""Markdown rendering for terminal output."""

from __future__ import annotations

from typing import Any
from rich.console import Console
from rich.markdown import Markdown as RichMarkdown

from clir.output.style import get_console


class Markdown:
    """Render markdown content in the terminal."""

    def __init__(
        self,
        code_theme: str = "monokai",
        justify: str | None = None,
        style: str | None = None,
    ):
        """Initialize markdown renderer.

        Args:
            code_theme: Syntax highlighting theme for code blocks
            justify: Text justification (default: None)
            style: Base style
        """
        self.code_theme = code_theme
        self.justify = justify
        self.style = style
        self.console = get_console()

    def render(self, markdown_text: str) -> None:
        """Render markdown to terminal.

        Args:
            markdown_text: Markdown content to render
        """
        md = Markdown.from_string(markdown_text, code_theme=self.code_theme)
        self.console.print(md, justify=self.justify, style=self.style)

    def __str__(self) -> str:
        return self._markdown_text if hasattr(self, '_markdown_text') else ""

    @staticmethod
    def from_string(markdown_text: str, code_theme: str = "monokai") -> RichMarkdown:
        """Create a Markdown instance from a string.

        Args:
            markdown_text: Markdown content
            code_theme: Syntax highlighting theme

        Returns:
            Rich Markdown object
        """
        return RichMarkdown(markdown_text, code_theme=code_theme)


def render_markdown(text: str, theme: str = "monokai") -> None:
    """Render markdown text to terminal.

    Args:
        text: Markdown content
        theme: Code highlighting theme
    """
    md = Markdown(code_theme=theme)
    md.render(text)


def print_markdown(text: str, theme: str = "monokai") -> None:
    """Print markdown with short name.

    Args:
        text: Markdown content
        theme: Code highlighting theme
    """
    render_markdown(text, theme)


__all__ = ["Markdown", "render_markdown", "print_markdown"]