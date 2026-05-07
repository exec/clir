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
