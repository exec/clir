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
