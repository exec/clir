"""Tests for output components."""

import pytest
from io import StringIO

from clir.output.style import echo, success, error, warning, info, debug
from clir.output.spinner import Spinner
from clir.output.progress import Progress
from clir.output.panel import Panel
from clir.output.table import Table


class TestStyle:
    """Tests for style output functions."""

    def test_echo(self, capsys):
        """Test echo outputs to stdout."""
        echo("Hello", "World")
        captured = capsys.readouterr()
        assert "Hello World" in captured.out

    def test_success(self, capsys):
        """Test success outputs styled text."""
        success("Operation completed")
        captured = capsys.readouterr()
        assert "Operation completed" in captured.out

    def test_error(self, capsys):
        """Test error outputs styled text."""
        error("Something went wrong")
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.out

    def test_warning(self, capsys):
        """Test warning outputs styled text."""
        warning("This is a warning")
        captured = capsys.readouterr()
        assert "This is a warning" in captured.out

    def test_info(self, capsys):
        """Test info outputs styled text."""
        info("Some information")
        captured = capsys.readouterr()
        assert "Some information" in captured.out

    def test_debug(self, capsys):
        """Test debug outputs styled text."""
        debug("Debug message")
        captured = capsys.readouterr()
        assert "Debug message" in captured.out


class TestSpinner:
    """Tests for Spinner class."""

    def test_spinner_context_manager(self, capsys):
        """Test spinner works as context manager."""
        with Spinner("Loading..."):
            pass
        captured = capsys.readouterr()
        # Should complete without error

    def test_spinner_with_message(self, capsys):
        """Test spinner with custom message."""
        with Spinner("Processing"):
            pass

    def test_spinner_custom_name(self, capsys):
        """Test spinner with custom spinner name."""
        with Spinner("Working", spinner_name="star"):
            pass


class TestProgress:
    """Tests for Progress class."""

    def test_progress_context_manager(self, capsys):
        """Test progress works as context manager."""
        with Progress("Downloading"):
            pass

    def test_progress_with_total(self, capsys):
        """Test progress with total set."""
        with Progress("Processing") as p:
            p.set_total(100)
            p.update(50)

    def test_progress_update(self, capsys):
        """Test progress update method."""
        with Progress("Task") as p:
            p.set_total(100)
            p.update(10)
            p.update(20)


class TestPanel:
    """Tests for Panel class."""

    def test_panel_simple(self):
        """Test simple panel output."""
        from clir.testing import capture_output
        with capture_output() as (stdout, stderr):
            Panel("Hello World").show()
        output = stdout.getvalue()
        assert "Hello World" in output

    def test_panel_with_title(self):
        """Test panel with title."""
        from clir.testing import capture_output
        with capture_output() as (stdout, stderr):
            Panel("Content", title="My Panel").show()
        output = stdout.getvalue()
        assert "Content" in output
        assert "My Panel" in output


class TestTable:
    """Tests for Table class."""

    def test_table_add_row(self, capsys):
        """Test adding rows to table."""
        table = Table("Name", "Age")
        table.add_row("Alice", "30")
        table.add_row("Bob", "25")
        captured = capsys.readouterr()
        # Should complete without error

    def test_table_with_title(self, capsys):
        """Test table with title."""
        table = Table("Name", title="People")
        table.add_row("Alice")
        captured = capsys.readouterr()

    def test_table_chainable(self, capsys):
        """Test that add_row returns self for chaining."""
        table = Table("Name")
        result = table.add_row("Alice")
        assert result is table
