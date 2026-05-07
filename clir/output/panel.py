"""Panel containers for terminal output."""

from rich.panel import Panel as RichPanel
from rich.text import Text
from typing import Any

from clir.output.style import get_console


class Panel:
    """A panel container for terminal output."""

    def __init__(
        self,
        content: str | Any,
        title: str | None = None,
        border_style: str = "blue",
        expand: bool = True,
    ):
        """Initialize a panel.

        Args:
            content: Text or Rich renderable to display inside the panel.
            title: Optional title shown in the panel border.
            border_style: Rich style for the border (default: "blue").
            expand: Whether to expand the panel to fill the terminal width.
        """
        self.content = content
        self.title = title
        self.border_style = border_style
        self.expand = expand

    def show(self) -> "Panel":
        """Print the panel to stdout."""
        get_console().print(self._to_rich())
        return self

    def _to_rich(self) -> RichPanel:
        """Convert the Panel to a Rich Panel object."""
        return RichPanel(
            self.content,
            title=self.title,
            border_style=self.border_style,
            expand=self.expand,
        )

    def __rich__(self) -> RichPanel:
        """Rich render protocol."""
        return self._to_rich()
