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
