"""Tests for edge cases and async commands."""

import pytest

from clir import ClirApp, argument, option
from clir.testing import CliRunner


class TestEdgeCases:
    """Edge case tests for CLI."""

    def test_empty_arg_list(self):
        """Test running with empty argument list."""
        app = ClirApp(name="test")
        runner = CliRunner(app)
        result = runner.invoke([])
        # Should show help
        assert "Commands:" in result.output or result.exit_code == 0

    def test_very_long_string(self):
        """Test handling very long string arguments."""
        app = ClirApp(name="test")

        @app.command()
        @argument("text")
        def echo(text: str):
            print(text)

        runner = CliRunner(app)
        long_text = "a" * 10000
        result = runner.invoke(["echo", long_text])
        assert result.success

    def test_special_characters_in_arg(self):
        """Test handling special characters in arguments."""
        app = ClirApp(name="test")

        @app.command()
        @argument("text")
        def echo(text: str):
            print(text)

        runner = CliRunner(app)
        # Test with various special characters
        result = runner.invoke(["echo", "hello world! @#$%"])
        assert result.success

    def test_unicode_in_arg(self):
        """Test handling unicode in arguments."""
        app = ClirApp(name="test")

        @app.command()
        @argument("text")
        def echo(text: str):
            print(text)

        runner = CliRunner(app)
        result = runner.invoke(["echo", "café"])
        assert result.success

    def test_leading_dash_argument(self):
        """Test argument that starts with dash.

        Note: argparse interprets arguments starting with dash as options.
        This is expected behavior. Use -- to separate options from arguments.
        """
        app = ClirApp(name="test")

        @app.command()
        @argument("text")
        def echo(text: str):
            print(text)

        runner = CliRunner(app)
        # Using -- tells argparse this is a positional argument
        result = runner.invoke(["echo", "--", "-something"])
        assert result.success

    def test_option_with_dash_value(self):
        """Test option with value starting with dash."""
        app = ClirApp(name="test")

        @app.command()
        @option("--value")
        def cmd(value: str):
            print(value)

        runner = CliRunner(app)
        result = runner.invoke(["cmd", "--value", "-42"])
        assert result.success


class TestAsyncCommands:
    """Tests for async command functions."""

    def test_async_command(self):
        """Test running an async command."""
        import asyncio

        app = ClirApp(name="test")

        @app.command()
        @argument("name")
        async def greet(name: str):
            await asyncio.sleep(0)
            print(f"Hello, {name}!")

        runner = CliRunner(app)
        result = runner.invoke(["greet", "World"])
        assert result.success
        assert "Hello, World!" in result.output

    def test_async_command_with_option(self):
        """Test async command with options."""
        import asyncio

        app = ClirApp(name="test")

        @app.command()
        @option("--count", "-c", default=1)
        async def count(count: int):
            for i in range(count):
                print(i)

        runner = CliRunner(app)
        result = runner.invoke(["count", "--count", "3"])
        assert result.success

    def test_async_group_command(self):
        """Test async command under a group."""
        import asyncio

        app = ClirApp(name="test")

        @app.group()
        def db():
            """Database commands."""

        @db.command()
        @argument("table")
        async def query(table: str):
            await asyncio.sleep(0)
            print(f"Querying {table}")

        runner = CliRunner(app)
        result = runner.invoke(["db", "query", "users"])
        assert result.success
        assert "Querying users" in result.output


class TestErrorPaths:
    """Tests for error handling paths."""

    def test_missing_required_argument(self):
        """Test error when required argument is missing."""
        app = ClirApp(name="test")

        @app.command()
        @argument("name", required=True)
        def greet(name: str):
            print(f"Hello, {name}!")

        runner = CliRunner(app)
        # Without the command name or without the required arg
        result = runner.invoke(["greet"])
        # This should fail validation
        assert not result.success or "Error" in result.output

    def test_invalid_type_conversion(self):
        """Test error when type conversion fails."""
        app = ClirApp(name="test")

        @app.command()
        @argument("number", type=int)
        def double(number: int):
            print(number * 2)

        runner = CliRunner(app)
        result = runner.invoke(["double", "not_a_number"])
        # Should fail or handle gracefully
        assert not result.success or "Error" in result.output

    def test_unknown_option(self):
        """Test error for unknown option."""
        app = ClirApp(name="test")

        @app.command()
        def cmd():
            print("ok")

        runner = CliRunner(app)
        result = runner.invoke(["cmd", "--unknown-option"])
        assert not result.success

    def test_validator_failure(self):
        """Test that a validator returning None causes the command to fail."""
        app = ClirApp(name="test")

        @app.command()
        @argument("num", validator=lambda x: x if x > 0 else None)
        def positive(num: int):
            print(num)

        runner = CliRunner(app)
        # 0 fails the validator (not > 0); command should error, not run with None
        result = runner.invoke(["positive", "0"])
        assert not result.success
        assert result.exit_code == 1
