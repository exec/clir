"""Interactive table with row selection."""

from __future__ import annotations

from typing import Any, Sequence
from clir.output.table import Table as ClirTable
from clir.prompts.select import select


class SelectTable:
    """A table that supports row selection."""

    def __init__(
        self,
        *columns: str,
        title: str | None = None,
        show_header: bool = True,
        show_lines: bool = False,
        box: str | None = None,
    ):
        """Initialize the select table.

        Args:
            *columns: Column names
            title: Optional table title
            show_header: Whether to show header
            show_lines: Whether to show lines
            box: Box style
        """
        self._table = ClirTable(
            *columns,
            title=title,
            show_header=show_header,
            show_lines=show_lines,
            box=box,
        )
        self._columns = list(columns)
        self._rows: list[dict[str, Any]] = []
        self._row_labels: list[str] = []

    def add_row(self, *values: Any, label: str | None = None) -> "SelectTable":
        """Add a row to the table.

        Args:
            *values: Row values
            label: Optional label for selection (defaults to row number)

        Returns:
            Self for chaining
        """
        row_dict = dict(zip(self._columns, values))
        self._rows.append(row_dict)
        self._row_labels.append(label or str(len(self._rows)))
        return self

    def add_rows(self, rows: Sequence[Sequence[Any]], labels: Sequence[str] | None = None) -> "SelectTable":
        """Add multiple rows.

        Args:
            rows: Sequence of row values
            labels: Optional labels for each row

        Returns:
            Self for chaining
        """
        for i, row in enumerate(rows):
            label = labels[i] if labels else str(i + 1)
            self.add_row(*row, label=label)
        return self

    def show(self, prompt: str = "Select a row:") -> dict[str, Any] | None:
        """Show table and prompt for selection.

        Args:
            prompt: Selection prompt message

        Returns:
            Selected row as dict, or None if cancelled
        """
        # Display the table
        self._table.show()

        if not self._rows:
            print("No rows to select from.")
            return None

        # Build choices from row labels
        choices = [f"{label}: {self._format_row(row)}" for label, row in zip(self._row_labels, self._rows)]

        try:
            choice = select(choices=choices, message=prompt)
            # Extract the selected row
            idx = choices.index(choice)
            return self._rows[idx]
        except (KeyboardInterrupt, EOFError):
            return None

    def select(self, prompt: str = "Select a row:") -> dict[str, Any] | None:
        """Prompt for selection without showing table.

        Args:
            prompt: Selection prompt

        Returns:
            Selected row or None
        """
        if not self._rows:
            return None

        choices = [f"{label}: {self._format_row(row)}" for label, row in zip(self._row_labels, self._rows)]
        try:
            choice = select(choices=choices, message=prompt)
            idx = choices.index(choice)
            return self._rows[idx]
        except (KeyboardInterrupt, EOFError):
            return None

    def select_multiple(self, prompt: str = "Select rows:", min_select: int = 1) -> list[dict[str, Any]]:
        """Select multiple rows.

        Args:
            prompt: Selection prompt
            min_select: Minimum selections required

        Returns:
            List of selected rows
        """
        if not self._rows:
            return []

        choices = [f"{label}: {self._format_row(row)}" for label, row in zip(self._row_labels, self._rows)]

        # Simple multi-select using comma-separated input
        print(f"\n{prompt}")
        print("Enter numbers separated by commas (e.g., 1,3,5)")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")

        try:
            user_input = input("Selection: ").strip()
            if not user_input:
                return []

            indices = [int(x.strip()) - 1 for x in user_input.split(",")]
            return [self._rows[i] for i in indices if 0 <= i < len(self._rows)]
        except (ValueError, KeyboardInterrupt, EOFError):
            return []

    def _format_row(self, row: dict[str, Any]) -> str:
        """Format a row for display in choice list."""
        return ", ".join(f"{k}={v}" for k, v in row.items())


def select_table(*columns: str, **kwargs: Any) -> SelectTable:
    """Create an interactive select table.

    Args:
        *columns: Column names
        **kwargs: Additional table options

    Returns:
        SelectTable instance
    """
    return SelectTable(*columns, **kwargs)


__all__ = ["SelectTable", "select_table"]