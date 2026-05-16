"""Tests for CLI groups and subcommands."""

import pytest

from clir import ClirApp, argument, option, group
from clir.output import echo
from clir.testing import CliRunner


@pytest.fixture
def app_with_groups():
    """Create a test CLI app with groups."""
    app = ClirApp(name="git", description="Git CLI")

    @app.group()
    def config():
        """Configuration commands."""

    @config.command()
    @argument("key")
    @argument("value")
    def set(key: str, value: str):
        """Set a config value."""
        echo(f"Set {key}={value}")

    @config.command()
    @argument("key")
    def get(key: str):
        """Get a config value."""
        echo(f"Get {key}")

    @app.command()
    @argument("message")
    def commit(message: str):
        """Commit changes."""
        echo(f"Commit: {message}")

    return app


def test_basic_group_command(app_with_groups):
    """Test running a group command."""
    runner = CliRunner(app_with_groups)
    result = runner.invoke(["commit", "Initial commit"])

    assert result.success
    assert "Commit: Initial commit" in result.output


def test_group_with_subcommand(app_with_groups):
    """Test running a subcommand within a group."""
    runner = CliRunner(app_with_groups)
    result = runner.invoke(["config", "set", "user.name", "John"])

    assert result.success
    assert "Set user.name=John" in result.output


def test_group_get_subcommand(app_with_groups):
    """Test getting a config value."""
    runner = CliRunner(app_with_groups)
    result = runner.invoke(["config", "get", "user.name"])

    assert result.success
    assert "Get user.name" in result.output


def test_unknown_group_subcommand(app_with_groups):
    """Test unknown subcommand within a group."""
    runner = CliRunner(app_with_groups)
    result = runner.invoke(["config", "unknown", "arg"])

    # Unknown subcommand is a usage error -> exit 2 (matches argparse convention)
    assert not result.success
    assert result.exit_code == 2


def test_help_shows_groups_and_commands(app_with_groups):
    """Test that help shows both groups and commands."""
    runner = CliRunner(app_with_groups)
    result = runner.invoke(["--help"])

    assert result.success
    # Check that both 'config' (group) and 'commit' (command) are shown
    output = result.output + result.error
    assert "config" in output
    assert "commit" in output


def test_group_help_shows_subcommands(app_with_groups):
    """Test that group help shows subcommands."""
    runner = CliRunner(app_with_groups)
    result = runner.invoke(["config", "--help"])

    assert result.success
    assert "set" in result.output
    assert "get" in result.output


# Nested groups tests

@pytest.fixture
def nested_groups_app():
    """Create a test CLI app with nested groups."""
    app = ClirApp(name="docker", description="Docker CLI")

    @app.group()
    def container():
        """Container commands."""

    @container.group()
    def network():
        """Network commands."""

    @network.command()
    @argument("name")
    def connect(name: str):
        """Connect container to network."""
        echo(f"Connected to {name}")

    @container.command()
    @argument("name")
    def start(name: str):
        """Start a container."""
        echo(f"Started {name}")

    return app


def test_nested_groups(nested_groups_app):
    """Test nested groups work correctly."""
    runner = CliRunner(nested_groups_app)
    result = runner.invoke(["container", "network", "connect", "myapp"])

    assert result.success
    assert "Connected to myapp" in result.output


def test_nested_groups_parent_command(nested_groups_app):
    """Test parent group command still works."""
    runner = CliRunner(nested_groups_app)
    result = runner.invoke(["container", "start", "myapp"])

    assert result.success
    assert "Started myapp" in result.output


# Test with options on subcommands

@pytest.fixture
def app_with_options():
    """Create a test CLI app with options on subcommands."""
    app = ClirApp(name="mycli")

    @app.group()
    def db():
        """Database commands."""

    @db.command()
    @argument("table")
    @option("--dry-run", "-d", default=False)
    def migrate(table: str, dry_run: bool):
        """Migrate a table."""
        if dry_run:
            echo(f"Would migrate {table}")
        else:
            echo(f"Migrating {table}")

    return app


def test_option_on_subcommand(app_with_options):
    """Test options work on subcommands."""
    runner = CliRunner(app_with_options)
    result = runner.invoke(["db", "migrate", "users", "--dry-run"])

    assert result.success
    assert "Would migrate users" in result.output


def test_short_option_on_subcommand(app_with_options):
    """Test short options work on subcommands."""
    runner = CliRunner(app_with_options)
    result = runner.invoke(["db", "migrate", "users", "-d"])

    assert result.success
    assert "Would migrate users" in result.output
