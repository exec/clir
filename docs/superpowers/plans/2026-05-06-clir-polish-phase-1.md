# Clir Polish Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `--quiet/--verbose/--debug` actually gate output, give errors a real exception hierarchy with traceback-on-debug, and remove two pieces of dead code.

**Architecture:** Two new leaf modules (`clir/runtime.py` for a `ContextVar`-backed `Verbosity` state; `clir/errors.py` for a `ClirError` hierarchy). Output functions in `clir/output/style.py` consult `runtime.get_verbosity()` and split between stdout/stderr. `ClirApp._parse_global_flags` calls `runtime.set_verbosity(...)` after parsing. The two existing `except Exception` blocks in `ClirApp` collapse into a single `_handle_exception` that special-cases `ClirError`, `KeyboardInterrupt`, and pydantic `ValidationError`, and prints a traceback only when `--debug` is set.

**Tech Stack:** Python 3.10+, `rich` for styled output, `pydantic` for validation errors, `pytest` + `pytest-asyncio` for tests. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-06-clir-polish-phase-1-design.md`

---

## File Structure

| Action  | Path                                | Responsibility                                                                  |
|---------|-------------------------------------|---------------------------------------------------------------------------------|
| Create  | `clir/runtime.py`                   | `Verbosity` dataclass + `ContextVar` + `get_verbosity`/`set_verbosity`.         |
| Create  | `clir/errors.py`                    | `ClirError`, `UsageError`.                                                      |
| Modify  | `clir/config/__init__.py`           | Rebase `ConfigError` onto `ClirError`.                                          |
| Modify  | `clir/output/style.py`              | Add `_stderr_console`, gate output funcs on verbosity, route to right stream.   |
| Modify  | `clir/core/app.py`                  | Wire `set_verbosity` after flag parse; add `_handle_exception`; delete dead code. |
| Modify  | `clir/__init__.py`                  | Export `ClirError`, `UsageError`.                                               |
| Create  | `tests/test_verbosity.py`           | Tests for `Verbosity`/`ContextVar` and gated output.                            |
| Create  | `tests/test_errors.py`              | Tests for exception handler behavior end-to-end.                                |

---

## Task 0: Set up git repo for commits

**Files:**
- Modify: `.gitignore` (create if missing)

The codebase at `/Users/dylan/Developer/clir` is currently not a git repository (no `.git` directory). The plan uses frequent commits, so we initialize one first. If a repo already exists, this task is a no-op.

- [ ] **Step 1: Check whether `.git` exists**

Run: `test -d .git && echo "repo exists" || echo "needs init"`

- [ ] **Step 2: If needed, initialize repo and create `.gitignore`**

Skip this step if the previous step printed `repo exists`.

```bash
git init
```

Create `.gitignore` with this content:

```
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/
venv/
.coverage
dist/
build/
```

- [ ] **Step 3: Make the initial commit of the existing tree**

Skip this step if the repo already had commits.

```bash
git add .
git commit -m "chore: initial commit before phase-1 polish"
```

- [ ] **Step 4: Verify pytest works in this environment**

Run: `python -m pytest tests/ -q 2>&1 | tail -5`

If pytest is missing, install dev deps: `pip install -e ".[dev]"` then retry.
Expected: tests pass (or skip if fixtures missing). Do not proceed if collection errors out — fix imports first.

---

## Task 1: Add `Verbosity` dataclass and `ContextVar`

**Files:**
- Create: `clir/runtime.py`
- Test:   `tests/test_verbosity.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_verbosity.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_verbosity.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clir.runtime'`.

- [ ] **Step 3: Implement `clir/runtime.py`**

Create `clir/runtime.py`:

```python
"""Runtime state for clir applications.

Holds verbosity state in a ContextVar so it is async-safe and per-task,
allowing two concurrent ClirApp invocations in the same process to maintain
independent verbosity without stomping each other.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class Verbosity:
    """Verbosity flags for output gating."""

    quiet: bool = False
    verbose: bool = False
    debug: bool = False


_verbosity: ContextVar[Verbosity] = ContextVar(
    "clir_verbosity", default=Verbosity()
)


def get_verbosity() -> Verbosity:
    """Return the current verbosity for this context."""
    return _verbosity.get()


def set_verbosity(v: Verbosity) -> None:
    """Set the verbosity for the current context.

    Called once by ClirApp.run after parsing global flags. May also be called
    directly by library users who want to gate output without going through
    ClirApp.
    """
    _verbosity.set(v)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_verbosity.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add clir/runtime.py tests/test_verbosity.py
git commit -m "feat(runtime): add Verbosity dataclass and ContextVar"
```

---

## Task 2: Add `ClirError` hierarchy

**Files:**
- Create: `clir/errors.py`
- Test:   `tests/test_errors.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_errors.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_errors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clir.errors'`.

- [ ] **Step 3: Implement `clir/errors.py`**

Create `clir/errors.py`:

```python
"""Exception hierarchy for clir.

ClirError is the base for any framework-raised error. User commands may also
raise ClirError (or its subclasses) to surface a styled message and a
specific exit code without leaking a traceback.
"""

from __future__ import annotations


class ClirError(Exception):
    """Base class for framework-raised errors.

    Carries a human-readable message and an exit_code. The dispatcher prints
    the message via the styled error() function and exits with the given
    code, never showing a traceback unless --debug is set.
    """

    exit_code: int = 1

    def __init__(self, message: str, *, exit_code: int | None = None):
        super().__init__(message)
        self.message = message
        if exit_code is not None:
            self.exit_code = exit_code


class UsageError(ClirError):
    """Bad CLI input from the user (unknown command, missing arg, bad value).

    Conventionally exits with code 2 to distinguish from a runtime error.
    """

    exit_code = 2
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_errors.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add clir/errors.py tests/test_errors.py
git commit -m "feat(errors): add ClirError and UsageError hierarchy"
```

---

## Task 3: Rebase `ConfigError` onto `ClirError`

**Files:**
- Modify: `clir/config/__init__.py:36-38`
- Test:   `tests/test_errors.py`

- [ ] **Step 1: Add a failing test**

Append to `tests/test_errors.py`:

```python
def test_config_error_inherits_from_clir_error():
    from clir.config import ConfigError
    assert issubclass(ConfigError, ClirError)
    err = ConfigError("bad config")
    assert err.exit_code == 1
    assert isinstance(err, ClirError)
    assert isinstance(err, Exception)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_errors.py::test_config_error_inherits_from_clir_error -v`
Expected: FAIL — `ConfigError` is currently a plain `Exception`.

- [ ] **Step 3: Modify `clir/config/__init__.py`**

Replace the existing `ConfigError` definition (currently at lines 36-38):

```python
class ConfigError(Exception):
    """Error loading or parsing config file."""
    pass
```

with:

```python
from clir.errors import ClirError


class ConfigError(ClirError):
    """Error loading or parsing config file."""
    pass
```

The `from clir.errors import ClirError` line goes near the top of the file, alongside the existing imports. `clir.errors` has no internal dependencies, so this does not introduce a cycle.

- [ ] **Step 4: Run all tests to verify pass and no regressions**

Run: `python -m pytest tests/test_errors.py -v && python -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add clir/config/__init__.py tests/test_errors.py
git commit -m "refactor(config): rebase ConfigError onto ClirError"
```

---

## Task 4: Add a stderr console rebuilt by `_apply_theme`

**Files:**
- Modify: `clir/output/style.py:205-213`
- Test:   `tests/test_verbosity.py`

The stderr console must share the stdout console's theme. We rebuild both inside `_apply_theme` so theme changes can never drift between the two.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_verbosity.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_verbosity.py -v -k stderr_console`
Expected: FAIL with `ImportError: cannot import name 'get_stderr_console'`.

- [ ] **Step 3: Modify `_apply_theme` and add `get_stderr_console`**

In `clir/output/style.py`, replace the `_apply_theme` function (currently lines 205-213):

```python
def _apply_theme(name: str) -> None:
    """Apply a theme based on terminal capability."""
    global console

    theme_colors = _THEME_COLORS.get(name, _THEME_COLORS["default"])
    colors = theme_colors.get(TERMINAL_CAPABILITY, theme_colors["basic"])

    _custom_theme = Theme(colors)
    console = Console(theme=_custom_theme)
```

with:

```python
def _apply_theme(name: str) -> None:
    """Apply a theme based on terminal capability.

    Rebuilds both the stdout and stderr consoles so they always share a theme.
    """
    global console, _stderr_console

    theme_colors = _THEME_COLORS.get(name, _THEME_COLORS["default"])
    colors = theme_colors.get(TERMINAL_CAPABILITY, theme_colors["basic"])

    _custom_theme = Theme(colors)
    console = Console(theme=_custom_theme)
    _stderr_console = Console(theme=_custom_theme, stderr=True)
```

The existing module follows a pattern where the stdout `console` is implicitly created by the first `_apply_theme("default")` call at line 299 (no module-level `console = None` placeholder exists). Apply the same pattern for `_stderr_console` — no separate declaration is needed, because the module-level call to `_apply_theme("default")` at the bottom of the file initializes both. Verify by grepping after the edit: `grep -n "_stderr_console" clir/output/style.py` should show its assignment inside `_apply_theme` and one read in `get_stderr_console`. Then add a getter alongside the existing `get_console`:

```python
def get_stderr_console() -> Console:
    """Get the current stderr console instance.

    Like get_console(), always call this instead of importing _stderr_console
    directly — the instance is replaced when set_theme is called.
    """
    return _stderr_console
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `python -m pytest tests/test_verbosity.py -v -k stderr_console`
Expected: 2 PASS.

- [ ] **Step 5: Run full output test suite to check no regressions**

Run: `python -m pytest tests/test_output.py -v`
Expected: all PASS (existing tests unchanged).

- [ ] **Step 6: Commit**

```bash
git add clir/output/style.py tests/test_verbosity.py
git commit -m "feat(output): build stderr console alongside stdout in _apply_theme"
```

---

## Task 5: Gate output functions on verbosity, route stderr stuff to stderr

**Files:**
- Modify: `clir/output/style.py:302-329`
- Test:   `tests/test_verbosity.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_verbosity.py`:

```python
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
    new_stdout = Console(file=stdout_buf, force_terminal=False, theme=style.console.theme)
    new_stderr = Console(file=stderr_buf, force_terminal=False, theme=style._stderr_console.theme)

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_verbosity.py -v -k "quiet or default_verbosity or debug_flag or error_and_warning"`
Expected: FAIL — current implementations write everything to stdout and ignore verbosity.

- [ ] **Step 3: Replace the six output functions**

In `clir/output/style.py`, replace the existing function bodies (currently lines 302-329):

```python
def echo(*objects: object, sep: str = " ", end: str = "\n") -> None:
    """Print styled output."""
    console.print(*objects, sep=sep, end=end)


def success(*objects: object, sep: str = " ") -> None:
    """Print success message."""
    console.print("[success]", *objects, sep=sep)


def error(*objects: object, sep: str = " ") -> None:
    """Print error message."""
    console.print("[error]", *objects, sep=sep)


def warning(*objects: object, sep: str = " ") -> None:
    """Print warning message."""
    console.print("[warning]", *objects, sep=sep)


def info(*objects: object, sep: str = " ") -> None:
    """Print info message."""
    console.print("[info]", *objects, sep=sep)


def debug(*objects: object, sep: str = " ") -> None:
    """Print debug message."""
    console.print("[debug]", *objects, sep=sep)
```

with:

```python
def echo(*objects: object, sep: str = " ", end: str = "\n") -> None:
    """Print styled output. Always shown — user's escape hatch."""
    console.print(*objects, sep=sep, end=end)


def success(*objects: object, sep: str = " ") -> None:
    """Print success message to stdout. Suppressed by --quiet."""
    from clir.runtime import get_verbosity
    if get_verbosity().quiet:
        return
    console.print("[success]", *objects, sep=sep)


def info(*objects: object, sep: str = " ") -> None:
    """Print info message to stdout. Suppressed by --quiet."""
    from clir.runtime import get_verbosity
    if get_verbosity().quiet:
        return
    console.print("[info]", *objects, sep=sep)


def warning(*objects: object, sep: str = " ") -> None:
    """Print warning message to stderr. Suppressed by --quiet."""
    from clir.runtime import get_verbosity
    if get_verbosity().quiet:
        return
    _stderr_console.print("[warning]", *objects, sep=sep)


def error(*objects: object, sep: str = " ") -> None:
    """Print error message to stderr. Always shown."""
    _stderr_console.print("[error]", *objects, sep=sep)


def debug(*objects: object, sep: str = " ") -> None:
    """Print debug message to stderr. Only shown when --debug is set."""
    from clir.runtime import get_verbosity
    if not get_verbosity().debug:
        return
    _stderr_console.print("[debug]", *objects, sep=sep)
```

The `from clir.runtime import get_verbosity` is inside each function to avoid an import-time cycle if any module imports both `clir.runtime` and `clir.output` during initialization. (`runtime` does not import from `output`, so there is no cycle today, but the inline import keeps it robust against future refactors.)

- [ ] **Step 4: Run the new tests**

Run: `python -m pytest tests/test_verbosity.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the existing output tests for regressions**

Run: `python -m pytest tests/test_output.py -v`
Expected: all PASS. Existing `test_output.py` tests use `capture_output()` — confirm whether they capture stderr. If a test was implicitly relying on `error()`/`warning()` writing to stdout, fix it by reading the stderr buffer instead. The fix is per-test and small; do not change the production behavior.

If any test fails, the failure should be of the form "expected 'foo' in stdout but got nothing." Look at what the test was actually testing — `error("foo")` — and update its assertion to read from stderr. Commit the test update separately if more than one test changes.

- [ ] **Step 6: Commit**

```bash
git add clir/output/style.py tests/test_verbosity.py tests/test_output.py
git commit -m "feat(output): gate output funcs on verbosity, route diagnostics to stderr"
```

---

## Task 6: Wire `_parse_global_flags` to call `set_verbosity`

**Files:**
- Modify: `clir/core/app.py:88-153`
- Test:   `tests/test_verbosity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_verbosity.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_verbosity.py::test_parse_global_flags_sets_verbosity tests/test_verbosity.py::test_parse_global_flags_no_flags_leaves_default_verbosity -v`
Expected: FAIL — `_parse_global_flags` does not yet call `set_verbosity`.

- [ ] **Step 3: Add `set_verbosity` call at the end of `_parse_global_flags`**

In `clir/core/app.py`, find the `_parse_global_flags` method (line 88). Just before its `return new_argv` (line 153), add:

```python
        from clir.runtime import set_verbosity, Verbosity
        set_verbosity(Verbosity(quiet=self._quiet, verbose=self._verbose, debug=self._debug))
```

The full bottom of the method should now read:

```python
        # Also check for --json and --pretty after the command (for convenience)
        for arg in post_command:
            if arg == "--json" or arg == "-j":
                self._json_mode = True
            elif arg == "--pretty" or arg == "-p":
                self._pretty = True
            else:
                new_argv.append(arg)

        from clir.runtime import set_verbosity, Verbosity
        set_verbosity(Verbosity(quiet=self._quiet, verbose=self._verbose, debug=self._debug))

        return new_argv
```

- [ ] **Step 4: Run the new tests**

Run: `python -m pytest tests/test_verbosity.py -v`
Expected: all PASS.

- [ ] **Step 5: Run full test suite for regressions**

Run: `python -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add clir/core/app.py tests/test_verbosity.py
git commit -m "feat(app): wire _parse_global_flags to runtime.set_verbosity"
```

---

## Task 7: Centralize exception handling in `_handle_exception`

**Files:**
- Modify: `clir/core/app.py:301-368` (the two existing `try/except` blocks and surrounding handlers)
- Test:   `tests/test_errors.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_errors.py`:

```python
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
    app = _build_app(raises=RuntimeError("kaboom"))
    result = CliRunner(app).invoke(["boom"])
    assert result.exit_code == 1
    assert "RuntimeError" in result.error
    assert "kaboom" in result.error
    # Should NOT contain traceback markers
    assert "Traceback" not in result.error


def test_unknown_exception_with_debug_flag_shows_traceback():
    app = _build_app(raises=RuntimeError("kaboom"))
    result = CliRunner(app).invoke(["--debug", "boom"])
    assert result.exit_code == 1
    assert "Traceback" in result.error or "kaboom" in result.error


def test_pydantic_validation_error_exit_2_per_field():
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_errors.py -v`
Expected: FAILs across all the new integration tests (`_handle_exception` does not yet exist; current code prints `Error: {e}` and exits 1 for everything).

- [ ] **Step 3: Add `_handle_exception` method**

In `clir/core/app.py`, add this method on `ClirApp` (place it right above `_run_command` near line 352):

```python
    def _handle_exception(self, exc: BaseException) -> "NoReturn":
        """Centralized exception handler.

        Always exits the process. Special-cases ClirError, KeyboardInterrupt,
        and pydantic ValidationError. Falls back to a short error line for
        unknown exceptions, with the full traceback shown only when --debug
        is set.
        """
        import sys
        import traceback
        from clir.errors import ClirError
        from clir.output import error as print_error
        from clir.runtime import get_verbosity

        try:
            from pydantic import ValidationError as PydanticValidationError
        except ImportError:  # pragma: no cover
            PydanticValidationError = None  # type: ignore[assignment]

        if isinstance(exc, KeyboardInterrupt):
            print("Aborted.", file=sys.stderr)
            sys.exit(130)

        if isinstance(exc, ClirError):
            print_error(exc.message)
            sys.exit(exc.exit_code)

        if PydanticValidationError is not None and isinstance(exc, PydanticValidationError):
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                print_error(f"{loc}: {err['msg']}")
            sys.exit(2)

        # Unknown exception
        if get_verbosity().debug:
            traceback.print_exc()
        else:
            print_error(f"{type(exc).__name__}: {exc}")
            print("Run with --debug to see the full traceback.", file=sys.stderr)
        sys.exit(1)
```

Note: The `NoReturn` type is imported via the existing `from typing import Any, Callable` line — extend it: `from typing import Any, Callable, NoReturn`.

- [ ] **Step 4: Replace the body of the existing `_run_command` `except` block**

In `clir/core/app.py`, replace the existing `_run_command` method (currently lines 352-368):

```python
    async def _run_command(
        self, cmd: Command | Group, args: dict[str, Any], parent: Context | None = None
    ) -> None:
        """Run a command with the given arguments."""
        try:
            result = await cmd.run(args, parent=parent)

            # Handle JSON output mode
            if self._json_mode and result is not None:
                import json
                if self._pretty:
                    print(json.dumps(result, indent=2, default=str))
                else:
                    print(json.dumps(result, default=str))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
```

with:

```python
    async def _run_command(
        self, cmd: Command | Group, args: dict[str, Any], parent: Context | None = None
    ) -> None:
        """Run a command with the given arguments."""
        try:
            result = await cmd.run(args, parent=parent)

            # Handle JSON output mode
            if self._json_mode and result is not None:
                import json
                if self._pretty:
                    print(json.dumps(result, indent=2, default=str))
                else:
                    print(json.dumps(result, default=str))
        except (Exception, KeyboardInterrupt) as e:
            self._handle_exception(e)
```

- [ ] **Step 5: Replace the body of the `_run_group_command` `except` block**

In `clir/core/app.py`, replace the existing `_run_group_command` `try/except` (currently lines 346-350):

```python
            parsed = vars(group_parser.parse_args(argv))
            try:
                asyncio.run(group.run(parsed, parent=None))
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
```

with:

```python
            parsed = vars(group_parser.parse_args(argv))
            try:
                asyncio.run(group.run(parsed, parent=None))
            except (Exception, KeyboardInterrupt) as e:
                self._handle_exception(e)
```

- [ ] **Step 6: Run the integration tests**

Run: `python -m pytest tests/test_errors.py -v`
Expected: all PASS.

- [ ] **Step 7: Run full test suite for regressions**

Run: `python -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add clir/core/app.py tests/test_errors.py
git commit -m "feat(app): centralize exception handling with traceback-on-debug"
```

---

## Task 8: Delete dead code

**Files:**
- Modify: `clir/core/app.py:138-140` (delete)
- Modify: `clir/core/app.py:168` (delete)

These are static deletions confirmed during design review. No tests change; existing tests should still pass.

- [ ] **Step 1: Delete the unreachable line at `app.py:168`**

Find this block:

```python
    @property
    def aliases(self) -> AliasManager:
        """Get the alias manager, creating if needed."""
        if self._alias_manager is None:
            self._alias_manager = AliasManager()
        return self._alias_manager
        self._aliases: dict[str, str] = {}  # alias -> command mapping
```

Delete the last line so it reads:

```python
    @property
    def aliases(self) -> AliasManager:
        """Get the alias manager, creating if needed."""
        if self._alias_manager is None:
            self._alias_manager = AliasManager()
        return self._alias_manager
```

- [ ] **Step 2: Delete the dead `--debug=` branch at `app.py:138-140`**

Find this block in `_parse_global_flags`:

```python
            elif arg == "--search" and i + 1 < len(pre_command):
                self._search = pre_command[i + 1]
                skip_next = True
            elif arg.startswith("--debug="):
                # Let argparse handle it
                new_argv.append(arg)
            else:
                new_argv.append(arg)
```

Delete the `--debug=` branch, leaving:

```python
            elif arg == "--search" and i + 1 < len(pre_command):
                self._search = pre_command[i + 1]
                skip_next = True
            else:
                new_argv.append(arg)
```

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -q`
Expected: all PASS — these are removals of unreachable / unused code.

- [ ] **Step 4: Commit**

```bash
git add clir/core/app.py
git commit -m "refactor(app): remove unreachable code and dead --debug= branch"
```

---

## Task 9: Export `ClirError` and `UsageError` from `clir/__init__.py`

**Files:**
- Modify: `clir/__init__.py:1-70`
- Test:   `tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_errors.py`:

```python
def test_clir_error_is_re_exported_from_top_level():
    import clir
    assert hasattr(clir, "ClirError")
    assert hasattr(clir, "UsageError")
    assert clir.ClirError is ClirError
    assert clir.UsageError is UsageError
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_errors.py::test_clir_error_is_re_exported_from_top_level -v`
Expected: FAIL — top-level `clir` does not yet expose these.

- [ ] **Step 3: Add the import and update `__all__`**

In `clir/__init__.py`, add this import alongside the others (e.g., after the `from clir.validation import ...` line):

```python
from clir.errors import ClirError, UsageError
```

Add to `__all__` (in the existing list, after the validation entries):

```python
    "ClirError",
    "UsageError",
```

- [ ] **Step 4: Run the test**

Run: `python -m pytest tests/test_errors.py -v`
Expected: all PASS.

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add clir/__init__.py tests/test_errors.py
git commit -m "feat(clir): re-export ClirError and UsageError"
```

---

## Final verification

- [ ] **Run all tests one last time**

Run: `python -m pytest tests/ -v`
Expected: every test passes, including the new `tests/test_verbosity.py` (~12 tests) and `tests/test_errors.py` (~12 tests).

- [ ] **Manual smoke test**

```bash
cd examples
python taskman.py --quiet add "buy milk"   # should not print success message
python taskman.py --debug list              # if a command raises, traceback should show
python taskman.py list 2>/dev/null          # warnings/errors should not appear here (they go to stderr)
```

- [ ] **Confirm `git log --oneline` shows the per-task commits**

Run: `git log --oneline | head -15`
Expected: 9 task commits + the initial commit, in order.

---

## Out of scope (Phase 2)

- Help unification (rich rendering for app/group/command --help).
- `run_async` entry point and shared event loop.

These will land in a separate plan: `docs/superpowers/plans/2026-05-MM-clir-polish-phase-2.md`.
