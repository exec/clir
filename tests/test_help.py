"""Tests for clir.help.render_help."""

import io
from unittest.mock import patch

from clir import ClirApp
from clir.help import render_help


def _capture_render(target, **kwargs) -> str:
    """Render help with stdout/stderr consoles patched to a StringIO buffer.

    Returns the captured output as a string.
    """
    from rich.console import Console
    from clir.output import style

    buf = io.StringIO()
    new_console = Console(file=buf, force_terminal=False)

    with patch.object(style, "console", new_console):
        render_help(target, **kwargs)

    return buf.getvalue()


def test_app_help_includes_usage_and_command_list():
    app = ClirApp(name="myapp", description="A test app.")

    @app.command()
    def hello():
        """Say hello."""
        pass

    @app.command()
    def goodbye():
        """Say goodbye."""
        pass

    out = _capture_render(app, app_name="myapp")
    assert "Usage:" in out
    assert "myapp" in out
    assert "A test app." in out
    assert "Commands:" in out
    assert "hello" in out
    assert "goodbye" in out
    assert "Say hello." in out
    assert "Say goodbye." in out


def test_app_help_with_search_filters_commands():
    app = ClirApp(name="myapp")

    @app.command()
    def alpha():
        """First."""
        pass

    @app.command()
    def beta():
        """Second."""
        pass

    out = _capture_render(app, app_name="myapp", search="alph")
    assert "alpha" in out
    assert "beta" not in out


def test_app_help_with_search_no_matches():
    app = ClirApp(name="myapp")

    @app.command()
    def alpha():
        """First."""
        pass

    out = _capture_render(app, app_name="myapp", search="zzz")
    assert "No commands found matching" in out


def test_group_help_includes_subcommands():
    app = ClirApp(name="myapp")

    @app.group()
    def db():
        """Database commands."""
        pass

    @db.command()
    def migrate():
        """Run migrations."""
        pass

    @db.command()
    def seed():
        """Seed data."""
        pass

    group = app.commands["db"]
    out = _capture_render(group, app_name="myapp")
    assert "Usage:" in out
    assert "myapp db" in out
    assert "Database commands." in out
    assert "migrate" in out
    assert "seed" in out
    assert "Run migrations." in out


def test_nested_group_uses_parent_path():
    app = ClirApp(name="myapp")

    @app.group()
    def db():
        """Database."""
        pass

    @db.group()
    def migrate():
        """Migrations."""
        pass

    @migrate.command()
    def up():
        """Run up migrations."""
        pass

    nested = app.commands["db"].commands["migrate"]
    out = _capture_render(nested, app_name="myapp", parent_path="db")
    assert "myapp db migrate" in out
    assert "up" in out


def test_command_help_includes_options_and_args():
    from clir import argument, option

    app = ClirApp(name="myapp")

    @app.command()
    @argument("name")
    @option("--count", "-c", default=1)
    def greet(name: str, count: int):
        """Greet someone."""
        pass

    cmd = app.commands["greet"]
    out = _capture_render(cmd, app_name="myapp")
    assert "Usage:" in out
    assert "myapp greet" in out
    assert "Greet someone." in out
    # Argument and option appear
    assert "name" in out
    assert "--count" in out


def test_command_help_with_no_params_still_renders():
    app = ClirApp(name="myapp")

    @app.command()
    def ping():
        """Just ping."""
        pass

    cmd = app.commands["ping"]
    out = _capture_render(cmd, app_name="myapp")
    assert "myapp ping" in out
    assert "Just ping." in out


def test_command_help_under_group_uses_parent_path():
    app = ClirApp(name="myapp")

    @app.group()
    def db():
        """DB."""
        pass

    @db.command()
    def migrate():
        """Migrate."""
        pass

    cmd = app.commands["db"].commands["migrate"]
    out = _capture_render(cmd, app_name="myapp", parent_path="db")
    assert "myapp db migrate" in out
