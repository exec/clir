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


def test_app_print_help_routes_through_render_help():
    """ClirApp._print_help is now a thin wrapper over render_help."""
    from clir.testing import CliRunner

    app = ClirApp(name="myapp", description="hi")

    @app.command()
    def hello():
        """Say hi."""
        pass

    runner = CliRunner(app)
    result = runner.invoke([])  # No args: should print app help
    assert "Commands:" in result.output
    assert "hello" in result.output
    assert "Say hi." in result.output


def test_app_print_help_with_search_query():
    from clir.testing import CliRunner

    app = ClirApp(name="myapp")

    @app.command()
    def alpha():
        """First."""
        pass

    @app.command()
    def beta():
        """Second."""
        pass

    runner = CliRunner(app)
    result = runner.invoke(["--search", "alph"])
    assert "alpha" in result.output
    assert "beta" not in result.output


def test_group_help_via_cli_runner_uses_render_help():
    """Running `app group --help` goes through render_help, not argparse default."""
    from clir.testing import CliRunner

    app = ClirApp(name="myapp")

    @app.group()
    def db():
        """Database commands."""
        pass

    @db.command()
    def migrate():
        """Run migrations."""
        pass

    runner = CliRunner(app)
    result = runner.invoke(["db", "--help"])
    # render_help-specific markers
    assert "myapp db" in result.output
    assert "Database commands." in result.output
    assert "Commands:" in result.output
    assert "migrate" in result.output
    assert "Run migrations." in result.output


def test_command_help_via_cli_runner_uses_render_help():
    """Running `app cmd --help` routes through render_help."""
    from clir.testing import CliRunner
    from clir import argument, option

    app = ClirApp(name="myapp")

    @app.command()
    @argument("name")
    @option("--loud", default=False)
    def greet(name: str, loud: bool):
        """Greet someone."""
        pass

    runner = CliRunner(app)
    result = runner.invoke(["greet", "--help"])
    # render_help-specific markers
    assert "Usage:" in result.output
    assert "myapp greet" in result.output
    assert "Greet someone." in result.output
    assert "Arguments:" in result.output or "name" in result.output
    assert "--loud" in result.output


def test_subcommand_under_group_help_uses_render_help():
    from clir.testing import CliRunner

    app = ClirApp(name="myapp")

    @app.group()
    def db():
        """DB."""
        pass

    @db.command()
    def migrate():
        """Migrate."""
        pass

    runner = CliRunner(app)
    result = runner.invoke(["db", "migrate", "--help"])
    assert "Usage:" in result.output
    assert "migrate" in result.output
    assert "Migrate." in result.output


# --- literal-bracket rendering ---------------------------------------------
# Help/description prose is plain text: literal [..] must render verbatim and
# not be swallowed as rich markup.


def test_app_description_renders_literal_brackets():
    app = ClirApp(
        name="myapp",
        description="Usage: myapp <cmd> [args...] (needs the [extra] package)",
    )
    out = _capture_render(app, app_name="myapp")
    assert "[args...]" in out
    assert "[extra]" in out


def test_app_usage_line_shows_bracketed_placeholders():
    app = ClirApp(name="myapp")

    @app.command()
    def hello():
        """Hi."""
        pass

    out = _capture_render(app, app_name="myapp")
    assert "[command]" in out
    assert "[options]" in out


def test_command_help_renders_literal_brackets():
    app = ClirApp(name="myapp")

    @app.command(help="[scaffold] stub — see file.py")
    def categorize():
        pass

    out = _capture_render(app.commands["categorize"], app_name="myapp")
    assert "[scaffold]" in out


def test_command_listing_help_renders_literal_brackets():
    app = ClirApp(name="myapp")

    @app.command(help="does a thing [default: off]")
    def run():
        pass

    out = _capture_render(app, app_name="myapp")
    assert "[default: off]" in out


def test_option_help_renders_literal_brackets():
    from clir import option

    app = ClirApp(name="myapp")

    @app.command()
    @option("--mode", help="mode [default: fast]")
    def run(mode):
        pass

    out = _capture_render(app.commands["run"], app_name="myapp")
    assert "[default: fast]" in out


def test_command_options_summary_shows_bracketed_placeholder():
    from clir import option

    app = ClirApp(name="myapp")

    @app.command()
    @option("--flag", help="a flag")
    def run(flag):
        pass

    out = _capture_render(app.commands["run"], app_name="myapp")
    assert "[options]" in out


def test_group_help_renders_literal_brackets():
    app = ClirApp(name="myapp")

    @app.group(help="manage things [advanced]")
    def db():
        pass

    @db.command()
    def migrate():
        """Migrate."""
        pass

    out = _capture_render(app.commands["db"], app_name="myapp")
    assert "[advanced]" in out
