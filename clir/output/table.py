"""Table builder for terminal output."""

import functools
import rich.box as _rich_box
from rich.table import Table as RichTable
from typing import Any, Sequence

from clir.output.style import get_console


@functools.lru_cache(maxsize=256)
def _to_string_cached(value: int | float | str | bool | None) -> str:
    """Convert a hashable value to string, cached."""
    return str(value)


def _to_string(value: Any) -> str:
    """Convert value to string, using cache for hashable values."""
    try:
        return _to_string_cached(value)
    except TypeError:
        return str(value)


class Table:
    """A table builder for terminal output."""

    def __init__(
        self,
        *columns: str,
        title: str | None = None,
        show_header: bool = True,
        show_lines: bool = False,
        box: str | None = None,
        style: str | None = None,
        width: int | None = None,
        min_width: int | None = None,
    ):
        """Initialize a table.

        Args:
            *columns: Column names
            title: Optional table title
            show_header: Whether to show header row
            show_lines: Whether to show lines between rows
            box: Box style name (e.g., 'simple', 'double', 'rounded')
            style: Table style (e.g., 'cyan', 'green')
            width: Fixed table width
            min_width: Minimum table width
        """
        self._table = RichTable(
            title=title,
            show_header=show_header,
            show_lines=show_lines,
            width=width,
            min_width=min_width,
            style=style or "",
        )

        # Set box style if provided
        if box:
            box_map = {
                'ascii': _rich_box.ASCII,
                'ascii2': _rich_box.ASCII2,
                'ascii_double_head': _rich_box.ASCII_DOUBLE_HEAD,
                'double': _rich_box.DOUBLE,
                'double_edge': _rich_box.DOUBLE_EDGE,
                'heavy': _rich_box.HEAVY,
                'heavy_edge': _rich_box.HEAVY_EDGE,
                'heavy_head': _rich_box.HEAVY_HEAD,
                'horizontals': _rich_box.HORIZONTALS,
                'markdown': _rich_box.MARKDOWN,
                'minimal': _rich_box.MINIMAL,
                'minimal_double_head': _rich_box.MINIMAL_DOUBLE_HEAD,
                'minimal_heavy_head': _rich_box.MINIMAL_HEAVY_HEAD,
                'rounded': _rich_box.ROUNDED,
                'simple': _rich_box.SIMPLE,
                'simple_head': _rich_box.SIMPLE_HEAD,
                'simple_heavy': _rich_box.SIMPLE_HEAVY,
                'square': _rich_box.SQUARE,
                'square_double_head': _rich_box.SQUARE_DOUBLE_HEAD,
            }
            if box in box_map:
                self._table.box = box_map[box]

        for col in columns:
            self._table.add_column(col)

    def add_row(self, *values: Any) -> "Table":
        """Add a row to the table."""
        self._table.add_row(*(_to_string(v) for v in values))
        return self

    def add_rows(self, rows: Sequence[Sequence[Any]]) -> "Table":
        """Add multiple rows to the table."""
        for row in rows:
            self._table.add_row(*(_to_string(v) for v in row))
        return self

    def show(self) -> "Table":
        """Print the table to stdout."""
        get_console().print(self._table)
        return self

    def __rich__(self) -> RichTable:
        """Rich render protocol."""
        return self._table

    @property
    def _rich_table(self) -> RichTable:
        """Access the underlying Rich Table object."""
        return self._table

    def to_csv(self, path: str | None = None) -> str:
        """Export table to CSV format.

        Args:
            path: Optional file path to write to

        Returns:
            CSV string
        """
        import csv
        import io

        output = io.StringIO()
        headers = [str(col.header) for col in self._table.columns]
        writer = csv.writer(output)
        writer.writerow(headers)

        # Get row data from table
        for row in self._table.rows:
            row_data = [str(cell) for cell in row.cells]
            writer.writerow(row_data)

        csv_content = output.getvalue()
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
        return csv_content

    def to_json(self, path: str | None = None) -> str:
        """Export table to JSON format.

        Args:
            path: Optional file path to write to

        Returns:
            JSON string
        """
        import json

        headers = [col.header for col in self._table.columns]
        rows = []

        for row in self._table.rows:
            row_dict = {}
            for i, cell in enumerate(row.cells):
                if i < len(headers):
                    row_dict[headers[i]] = str(cell)
            rows.append(row_dict)

        data = {
            "columns": headers,
            "rows": rows,
        }

        json_content = json.dumps(data, indent=2)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json_content)
        return json_content

    def to_csv(self, delimiter: str = ",") -> str:
        """Export table to CSV format.

        Args:
            delimiter: CSV delimiter

        Returns:
            CSV string
        """
        import io
        import csv

        output = io.StringIO()
        writer = csv.writer(output, delimiter=delimiter)

        # Write header
        if self._table.columns:
            writer.writerow([col.header.plain for col in self._table.columns])

        # Write rows
        for row in self._table.rows:
            writer.writerow([cell.plain for cell in row.cells])

        return output.getvalue()

    def to_json(self) -> str:
        """Export table to JSON format.

        Returns:
            JSON string
        """
        import json

        data = {
            "columns": [col.header.plain for col in self._table.columns],
            "rows": [
                [cell.plain for cell in row.cells]
                for row in self._table.rows
            ]
        }
        return json.dumps(data, indent=2)

    def export(self, path: str, format: str = "csv") -> None:
        """Export table to file.

        Args:
            path: Output file path
            format: Format ('csv' or 'json')
        """
        if format == "csv":
            content = self.to_csv()
        elif format == "json":
            content = self.to_json()
        else:
            raise ValueError(f"Unknown format: {format}")

        from pathlib import Path
        Path(path).write_text(content, encoding="utf-8")
