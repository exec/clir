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
