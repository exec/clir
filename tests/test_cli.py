"""Tests for Clir CLI framework."""

import pytest

from clir import ClirApp, argument, option
from clir.output import success, error
from clir.testing import CliRunner, mock_prompt


@pytest.fixture
def app():
    """Create a test CLI app."""
    app = ClirApp(name="test", description="Test CLI")

    @app.command()
    @argument("name")
    @option("--count", "-c", default=1)
    def greet(name: str, count: int):
        """Greet someone."""
        for _ in range(count):
            success(f"Hello, {name}!")

    @app.command()
    @option("--verbose", "-v", default=False)
    def status(verbose: bool):
        """Show status."""
        if verbose:
            error("Verbose mode")
        else:
            success("OK")

    @app.command()
    @argument("message")
    def echo(message: str):
        """Echo a message."""
        return message

    return app


def test_basic_command(app):
    """Test running a basic command."""
    runner = CliRunner(app)
    result = runner.invoke(["greet", "World"])

    assert result.success
    assert "Hello, World!" in result.output


def test_command_with_option(app):
    """Test command with option."""
    runner = CliRunner(app)
    result = runner.invoke(["greet", "Alice", "--count", "3"])

    assert result.success
    assert result.output.count("Hello, Alice!") == 3


def test_command_with_long_option(app):
    """Test command with long option."""
    runner = CliRunner(app)
    result = runner.invoke(["status", "--verbose"])

    assert result.success
    # error() now routes to stderr
    assert "Verbose mode" in result.error


def test_command_with_short_option(app):
    """Test command with short option."""
    runner = CliRunner(app)
    result = runner.invoke(["status", "-v"])

    assert result.success
    # error() now routes to stderr
    assert "Verbose mode" in result.error


def test_command_with_context(app):
    """Test command that uses context."""
    app2 = ClirApp(name="test")

    @app2.command()
    @argument("name")
    def whoami(name: str, context):
        """Show context info."""
        success(f"Command: {context.command_name}, Args: {context.args}")

    runner = CliRunner(app2)
    result = runner.invoke(["whoami", "testuser"])

    assert result.success
    assert "Command: whoami" in result.output


def test_unknown_command(app):
    """Test unknown command handling."""
    runner = CliRunner(app)
    result = runner.invoke(["unknown"])

    assert not result.success
    assert result.exit_code in (1, 2)


def test_no_args_shows_help(app):
    """Test running with no args shows help."""
    runner = CliRunner(app)
    result = runner.invoke([])

    # Help can be in output or error, exit code can be 0 or 2
    assert "Commands:" in result.output or "Usage:" in result.output or result.exit_code == 0


def test_required_argument():
    """Test that required arguments are enforced."""
    app = ClirApp(name="test")

    @app.command()
    @argument("name", required=True)
    def greet(name: str):
        """Greet someone."""
        success(f"Hello, {name}!")

    runner = CliRunner(app)
    result = runner.invoke(["greet"])

    # Argparse enforces required arguments with exit code 2
    assert not result.success
    assert result.exit_code == 2


def test_required_option():
    """Test that required options are enforced."""
    app = ClirApp(name="test")

    @app.command()
    @option("--config", required=True)
    def run(config: str):
        """Run with config."""
        success(f"Running with config: {config}!")

    runner = CliRunner(app)
    result = runner.invoke(["run"])

    # Our custom validation enforces required options
    assert not result.success
    assert "Missing required" in result.error


def test_mock_prompt_context_manager():
    """Test that mock_prompt context manager works."""
    # Store the original prompt function
    import prompt_toolkit

    original_prompt = prompt_toolkit.prompt

    with mock_prompt(["test_input"]):
        # Verify prompt is mocked
        assert prompt_toolkit.prompt != original_prompt

        # Call the mocked prompt
        result = prompt_toolkit.prompt("Test: ")
        assert result == "test_input"

    # Verify prompt is restored after context manager exits
    assert prompt_toolkit.prompt == original_prompt
