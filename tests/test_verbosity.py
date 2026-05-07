"""Tests for clir.runtime verbosity state."""

import asyncio
import pytest

from clir.runtime import Verbosity, get_verbosity, set_verbosity


def test_verbosity_defaults_to_all_false():
    v = Verbosity()
    assert v.quiet is False
    assert v.verbose is False
    assert v.debug is False


def test_verbosity_is_frozen():
    v = Verbosity(quiet=True)
    with pytest.raises(Exception):
        v.quiet = False  # frozen dataclass should reject this


def test_get_verbosity_default_is_all_false():
    # Reset to default by setting a fresh Verbosity()
    set_verbosity(Verbosity())
    v = get_verbosity()
    assert v == Verbosity()


def test_set_and_get_verbosity_roundtrip():
    set_verbosity(Verbosity(quiet=True, debug=True))
    v = get_verbosity()
    assert v.quiet is True
    assert v.debug is True
    assert v.verbose is False
    # Cleanup
    set_verbosity(Verbosity())


def test_verbosity_contextvar_isolates_async_tasks():
    """Verbosity set in one task should not leak into a sibling task."""

    set_verbosity(Verbosity())

    async def task_a():
        set_verbosity(Verbosity(quiet=True))
        await asyncio.sleep(0)
        return get_verbosity()

    async def task_b():
        await asyncio.sleep(0)
        return get_verbosity()

    async def main():
        # Run them as separate tasks so they get independent ContextVar copies
        ta = asyncio.create_task(task_a())
        tb = asyncio.create_task(task_b())
        return await ta, await tb

    a_v, b_v = asyncio.run(main())
    assert a_v.quiet is True
    assert b_v.quiet is False
    # Cleanup
    set_verbosity(Verbosity())


def test_stderr_console_is_built_alongside_stdout_console():
    from clir.output.style import _apply_theme, get_console, get_stderr_console
    _apply_theme("default")
    stdout = get_console()
    stderr = get_stderr_console()
    assert stderr is not None
    assert stderr is not stdout
    # Apply a different theme; both should be rebuilt
    _apply_theme("monokai")
    new_stdout = get_console()
    new_stderr = get_stderr_console()
    assert new_stdout is not stdout
    assert new_stderr is not stderr
    # Reset
    _apply_theme("default")


def test_stderr_console_writes_to_stderr_stream():
    from clir.output.style import get_stderr_console
    c = get_stderr_console()
    # Rich Console exposes the file it writes to
    assert c.file is not None
    # rich's Console with stderr=True writes to sys.stderr
    import sys
    assert c.file is sys.stderr


import io
from unittest.mock import patch

from clir.runtime import Verbosity, set_verbosity


def _capture_streams():
    """Patch the stdout and stderr consoles to write to StringIOs we can read.

    Returns (stdout_buf, stderr_buf, patches_to_exit).
    """
    from rich.console import Console
    from clir.output import style

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    new_stdout = Console(file=stdout_buf, force_terminal=False)
    new_stderr = Console(file=stderr_buf, force_terminal=False)

    p_stdout = patch.object(style, "console", new_stdout)
    p_stderr = patch.object(style, "_stderr_console", new_stderr)
    return stdout_buf, stderr_buf, p_stdout, p_stderr


def test_quiet_suppresses_success_info_warning_but_not_error():
    set_verbosity(Verbosity(quiet=True))
    stdout, stderr, p_out, p_err = _capture_streams()
    with p_out, p_err:
        from clir.output.style import success, info, warning, error, echo
        success("hello-success")
        info("hello-info")
        warning("hello-warning")
        error("hello-error")
        echo("hello-echo")
    assert "hello-success" not in stdout.getvalue()
    assert "hello-info" not in stdout.getvalue()
    assert "hello-warning" not in stderr.getvalue()
    assert "hello-error" in stderr.getvalue()
    assert "hello-echo" in stdout.getvalue()
    set_verbosity(Verbosity())


def test_default_verbosity_suppresses_only_debug():
    set_verbosity(Verbosity())
    stdout, stderr, p_out, p_err = _capture_streams()
    with p_out, p_err:
        from clir.output.style import success, info, warning, error, debug, echo
        success("a-success")
        info("a-info")
        warning("a-warning")
        error("a-error")
        debug("a-debug")
        echo("a-echo")
    assert "a-success" in stdout.getvalue()
    assert "a-info" in stdout.getvalue()
    assert "a-warning" in stderr.getvalue()
    assert "a-error" in stderr.getvalue()
    assert "a-debug" not in stderr.getvalue()
    assert "a-echo" in stdout.getvalue()


def test_debug_flag_enables_debug_output():
    set_verbosity(Verbosity(debug=True))
    stdout, stderr, p_out, p_err = _capture_streams()
    with p_out, p_err:
        from clir.output.style import debug
        debug("d-line")
    assert "d-line" in stderr.getvalue()
    set_verbosity(Verbosity())


def test_error_and_warning_go_to_stderr_not_stdout():
    set_verbosity(Verbosity())
    stdout, stderr, p_out, p_err = _capture_streams()
    with p_out, p_err:
        from clir.output.style import error, warning
        error("err-line")
        warning("warn-line")
    assert "err-line" not in stdout.getvalue()
    assert "warn-line" not in stdout.getvalue()
    assert "err-line" in stderr.getvalue()
    assert "warn-line" in stderr.getvalue()


def test_parse_global_flags_sets_verbosity():
    from clir import ClirApp
    from clir.runtime import get_verbosity, set_verbosity, Verbosity

    set_verbosity(Verbosity())  # baseline
    app = ClirApp(name="x")
    rest = app._parse_global_flags(["--quiet", "--debug", "cmd", "arg"])
    v = get_verbosity()
    assert v.quiet is True
    assert v.debug is True
    assert v.verbose is True  # --debug implies --verbose per existing logic
    assert rest == ["cmd", "arg"]
    set_verbosity(Verbosity())


def test_parse_global_flags_no_flags_leaves_default_verbosity():
    from clir import ClirApp
    from clir.runtime import get_verbosity, set_verbosity, Verbosity

    set_verbosity(Verbosity())
    app = ClirApp(name="x")
    rest = app._parse_global_flags(["cmd", "arg"])
    v = get_verbosity()
    assert v == Verbosity()
    assert rest == ["cmd", "arg"]
