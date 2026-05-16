"""Tests for clir.errors and the centralized exception handler."""

import pytest

from clir.errors import ClirError, UsageError


def test_clir_error_default_exit_code_is_1():
    err = ClirError("boom")
    assert err.exit_code == 1
    assert err.message == "boom"
    assert str(err) == "boom"


def test_clir_error_custom_exit_code():
    err = ClirError("boom", exit_code=7)
    assert err.exit_code == 7


def test_usage_error_default_exit_code_is_2():
    err = UsageError("bad flag")
    assert err.exit_code == 2
    assert err.message == "bad flag"


def test_usage_error_inherits_from_clir_error():
    err = UsageError("bad flag")
    assert isinstance(err, ClirError)


def test_clir_error_is_an_exception():
    with pytest.raises(ClirError):
        raise ClirError("boom")


def test_config_error_inherits_from_clir_error():
    from clir.config import ConfigError
    assert issubclass(ConfigError, ClirError)
    err = ConfigError("bad config")
    assert err.exit_code == 1
    assert isinstance(err, ClirError)
    assert isinstance(err, Exception)


"""Integration tests for the centralized exception handler."""

from clir import ClirApp
from clir.errors import ClirError, UsageError
from clir.testing import CliRunner
from pydantic import BaseModel, ValidationError


def _build_app(*, raises):
    app = ClirApp(name="x")

    @app.command()
    def boom():
        raise raises

    return app


def test_clir_error_exit_code_and_message():
    app = _build_app(raises=ClirError("user-message", exit_code=7))
    result = CliRunner(app).invoke(["boom"])
    assert result.exit_code == 7
    assert "user-message" in result.error


def test_usage_error_exit_code_2():
    app = _build_app(raises=UsageError("bad usage"))
    result = CliRunner(app).invoke(["boom"])
    assert result.exit_code == 2
    assert "bad usage" in result.error


def test_keyboard_interrupt_exit_130():
    app = _build_app(raises=KeyboardInterrupt())
    result = CliRunner(app).invoke(["boom"])
    assert result.exit_code == 130
    assert "Aborted" in result.error


def test_unknown_exception_short_message_no_traceback_by_default():
    from clir.runtime import set_verbosity, Verbosity
    set_verbosity(Verbosity())
    app = _build_app(raises=RuntimeError("kaboom"))
    result = CliRunner(app).invoke(["boom"])
    assert result.exit_code == 1
    assert "RuntimeError" in result.error
    assert "kaboom" in result.error
    # Should NOT contain traceback markers
    assert "Traceback" not in result.error


def test_unknown_exception_with_debug_flag_shows_traceback():
    from clir.runtime import set_verbosity, Verbosity
    try:
        app = _build_app(raises=RuntimeError("kaboom"))
        result = CliRunner(app).invoke(["--debug", "boom"])
        assert result.exit_code == 1
        assert "Traceback" in result.error
    finally:
        set_verbosity(Verbosity())


def test_pydantic_validation_error_exit_2_per_field():
    from clir.runtime import set_verbosity, Verbosity
    set_verbosity(Verbosity())

    class M(BaseModel):
        x: int

    try:
        M(x="not-an-int")
    except ValidationError as e:
        captured = e

    app = _build_app(raises=captured)
    result = CliRunner(app).invoke(["boom"])
    assert result.exit_code == 2
    assert "x" in result.error


def test_clir_error_is_re_exported_from_top_level():
    import clir
    assert hasattr(clir, "ClirError")
    assert hasattr(clir, "UsageError")
    assert clir.ClirError is ClirError
    assert clir.UsageError is UsageError


"""Usage-error routing: missing args, bad values, and unknown commands all
surface as UsageError-equivalent (clean message, exit 2, no traceback hint)."""

from clir import argument, option


def test_missing_required_option_is_usage_error():
    app = ClirApp(name="x")

    @app.command()
    @option("--project", required=True)
    def synthesize(project):
        pass

    result = CliRunner(app).invoke(["synthesize"])
    assert result.exit_code == 2
    assert "Missing required argument(s): --project" in result.error
    # Rendered cleanly: no bare exception class name, no debug-traceback hint.
    assert "ValueError" not in result.error
    assert "--debug" not in result.error


def test_missing_required_argument_is_usage_error():
    app = ClirApp(name="x")

    @app.command()
    @argument("name", required=True)
    @option("--unused", default="x")
    def pick(name, unused):
        pass

    # An argument with no value and no default reaches Command.run as required.
    result = CliRunner(app).invoke(["pick"])
    assert result.exit_code == 2


def test_validator_failure_is_usage_error():
    app = ClirApp(name="x")

    @app.command()
    @argument("num", type=int, validator=lambda v: v if v > 0 else None)
    def positive(num):
        pass

    result = CliRunner(app).invoke(["positive", "0"])
    assert result.exit_code == 2
    assert "validation failed" in result.error
    assert "ValueError" not in result.error
    assert "--debug" not in result.error


def test_unknown_command_exits_2():
    app = ClirApp(name="x")

    @app.command()
    def hello():
        pass

    result = CliRunner(app).invoke(["nonsense"])
    assert result.exit_code == 2
    assert "Unknown command" in result.error


def test_unknown_command_keeps_did_you_mean_suggestion():
    app = ClirApp(name="x")

    @app.command()
    def status():
        pass

    result = CliRunner(app).invoke(["staus"])  # typo
    assert result.exit_code == 2
    assert "Did you mean" in result.error


def test_unknown_group_subcommand_exits_2():
    app = ClirApp(name="x")

    @app.group()
    def db():
        """DB commands."""

    @db.command()
    def migrate():
        pass

    result = CliRunner(app).invoke(["db", "nonsense"])
    assert result.exit_code == 2


def test_group_with_no_subcommand_exits_2():
    app = ClirApp(name="x")

    @app.group()
    def db():
        """DB commands."""

    @db.command()
    def migrate():
        pass

    result = CliRunner(app).invoke(["db"])
    assert result.exit_code == 2
