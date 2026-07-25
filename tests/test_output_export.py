"""Regression tests for the reconciled output helpers.

Three modules each defined functions twice, with the second definition
silently replacing the first at import time:

  - ``clir.output.table``    -> ``Table.to_csv`` / ``Table.to_json``
  - ``clir.output.progress`` -> ``ansi_progress`` / ``print_ansi_progress``
  - ``clir.output.style``    -> ``get_recommended_theme`` / ``auto_theme``

For the table the surviving definitions had dropped the ``path=`` argument, so
``Table.to_csv(path=...)`` raised ``TypeError`` instead of writing a file. Both
variants were also reading rows via ``Row.cells`` / ``Column.header.plain``,
neither of which exists in Rich — so CSV/JSON export crashed outright.
"""

import inspect
import json

import pytest

from clir.output import progress as progress_mod
from clir.output import style as style_mod
from clir.output.progress import ansi_progress, print_ansi_progress
from clir.output.table import Table


@pytest.fixture
def people() -> Table:
    return Table("Name", "Age").add_row("Alice", 30).add_row("Bob", 25)


def read_raw(path) -> str:
    """Read a file without newline translation.

    ``Path.read_text(newline=...)`` only exists on 3.13+, and the CSV line
    terminators are exactly what these tests are checking.
    """
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


class TestTableToCsv:
    """Tests for Table.to_csv, including the restored path= writing."""

    def test_returns_csv_string(self, people):
        assert people.to_csv() == "Name,Age\r\nAlice,30\r\nBob,25\r\n"

    def test_header_only_when_no_rows(self):
        assert Table("Name", "Age").to_csv() == "Name,Age\r\n"

    def test_empty_table(self):
        assert Table().to_csv() == "\r\n"

    def test_custom_delimiter(self, people):
        assert people.to_csv(delimiter="\t").splitlines()[0] == "Name\tAge"

    def test_path_writes_file(self, people, tmp_path):
        """The restored path= argument writes the CSV to disk."""
        dest = tmp_path / "people.csv"
        returned = people.to_csv(path=dest)

        assert read_raw(dest) == returned
        assert dest.read_text(encoding="utf-8").splitlines() == [
            "Name,Age",
            "Alice,30",
            "Bob,25",
        ]

    def test_path_accepts_str(self, people, tmp_path):
        dest = tmp_path / "people.csv"
        people.to_csv(path=str(dest))
        assert "Alice,30" in dest.read_text(encoding="utf-8")

    def test_path_is_positional_too(self, people, tmp_path):
        dest = tmp_path / "people.csv"
        people.to_csv(dest)
        assert dest.exists()


class TestTableToJson:
    """Tests for Table.to_json, including the restored path= writing."""

    def test_returns_column_and_row_dicts(self, people):
        assert json.loads(people.to_json()) == {
            "columns": ["Name", "Age"],
            "rows": [
                {"Name": "Alice", "Age": "30"},
                {"Name": "Bob", "Age": "25"},
            ],
        }

    def test_no_rows(self):
        assert json.loads(Table("Name").to_json()) == {"columns": ["Name"], "rows": []}

    def test_path_writes_file(self, people, tmp_path):
        """The restored path= argument writes the JSON to disk."""
        dest = tmp_path / "people.json"
        returned = people.to_json(path=dest)

        assert dest.read_text(encoding="utf-8") == returned
        assert json.loads(dest.read_text(encoding="utf-8"))["rows"][0]["Name"] == "Alice"

    def test_indent_is_configurable(self, people):
        assert "\n" not in people.to_json(indent=None)


class TestTableExport:
    """Table.export delegates to the to_csv/to_json path= writing."""

    def test_export_csv(self, people, tmp_path):
        dest = tmp_path / "out.csv"
        people.export(dest, format="csv")
        assert read_raw(dest) == people.to_csv()

    def test_export_json(self, people, tmp_path):
        dest = tmp_path / "out.json"
        people.export(dest, format="json")
        assert json.loads(dest.read_text(encoding="utf-8"))["columns"] == ["Name", "Age"]

    def test_export_unknown_format(self, people, tmp_path):
        with pytest.raises(ValueError, match="Unknown format"):
            people.export(tmp_path / "out.xml", format="xml")


class TestAnsiProgress:
    """The surviving ansi_progress keeps the fuller show_percentage API."""

    def test_show_percentage_is_supported(self):
        assert ansi_progress(5, 10, width=10) == f"[{'█' * 5}{'░' * 5}] 50%"

    def test_percentage_can_be_suppressed(self):
        assert ansi_progress(5, 10, width=10, show_percentage=False).endswith("]")

    def test_prefix(self):
        assert ansi_progress(0, 10, width=4, prefix="Downloading: ").startswith(
            "Downloading: "
        )

    def test_zero_total_does_not_divide_by_zero(self):
        assert ansi_progress(0, 0, width=4) == f"[{'░' * 4}] 0%"

    def test_bar_never_exceeds_width(self):
        bar = ansi_progress(50, 10, width=10, show_percentage=False)
        assert bar == f"[{'█' * 10}]"

    def test_print_ansi_progress_accepts_show_percentage(self, capsys):
        print_ansi_progress(10, 10, width=4, show_percentage=False)
        out = capsys.readouterr().out
        assert out.startswith("\r[")
        assert out.endswith("\n")  # newline once complete


class TestSingleDefinitions:
    """Each reconciled name must be defined exactly once per module."""

    @pytest.mark.parametrize(
        "module, names",
        [
            (progress_mod, ["ansi_progress", "print_ansi_progress"]),
            (
                style_mod,
                [
                    "get_recommended_theme",
                    "auto_theme",
                    "_DARK_THEMES",
                    "_LIGHT_THEMES",
                ],
            ),
        ],
    )
    def test_module_level_names_defined_once(self, module, names):
        source = inspect.getsource(module)
        for name in names:
            definitions = [
                line
                for line in source.splitlines()
                if line.startswith((f"def {name}(", f"{name} ="))
            ]
            assert len(definitions) == 1, f"{name} defined {len(definitions)} times"

    def test_table_methods_defined_once(self):
        source = inspect.getsource(Table)
        for name in ("to_csv", "to_json", "export"):
            assert source.count(f"    def {name}(") == 1

    def test_theme_recommendation_still_works(self):
        assert style_mod.get_recommended_theme() in style_mod.get_available_themes()
