# Clir Polish — Phase 1: Wiring + Error Story

**Date:** 2026-05-06
**Scope:** Phase 1 of a two-phase polish pass on `clir`. Phase 2 (help unification, asyncio loop sharing) has its own spec.

## Motivation

The `clir` framework documents and parses several global flags and error behaviors that don't actually work end-to-end:

- `--quiet`, `--verbose`, `--debug` are parsed by `ClirApp._parse_global_flags` and stored on the app, but the output functions (`success`, `error`, `info`, `debug`, etc.) never read them. Users get no quieting and no debug-only output.
- The two `except Exception as e: print(f"Error: {e}"); sys.exit(1)` sites in `core/app.py` swallow tracebacks unconditionally — even when `--debug` is set.
- `clir/core/app.py:168` contains an unreachable `self._aliases: dict[str, str] = {}` after a `return` — leftover from a refactor.
- `clir/core/app.py:138-140` forwards `--debug=...` strings to argparse, but argparse has no `--debug` argument registered, so this branch is either dead or actively broken.

Phase 1 fixes these correctness gaps without changing the public API. Existing examples and tests continue to work.

## Non-goals

- Help-output unification (Phase 2).
- Asyncio loop sharing / `run_async` entry point (Phase 2).
- New features or output components.
- Backward-incompatible changes to the output function signatures.

## Design

### 1. Verbosity runtime (`clir/runtime.py`)

A new module owns a single `ContextVar` for verbosity state:

```python
from contextvars import ContextVar
from dataclasses import dataclass

@dataclass(frozen=True)
class Verbosity:
    quiet: bool = False
    verbose: bool = False
    debug: bool = False

_verbosity: ContextVar[Verbosity] = ContextVar("clir_verbosity", default=Verbosity())

def get_verbosity() -> Verbosity:
    return _verbosity.get()

def set_verbosity(v: Verbosity) -> None:
    _verbosity.set(v)
```

ContextVars are async-safe and per-task, so two concurrent `ClirApp.run_async` invocations do not stomp each other's verbosity state. They also propagate naturally through `await`.

### 2. Output gating (`clir/output/style.py`)

Each output function consults `runtime.get_verbosity()` and gates itself:

| Function   | Stream  | Behavior under flags                                                      |
|------------|---------|---------------------------------------------------------------------------|
| `echo`     | stdout  | Always prints (user's escape hatch).                                      |
| `success`  | stdout  | Suppressed if `quiet`.                                                    |
| `info`     | stdout  | Suppressed if `quiet`.                                                    |
| `warning`  | stderr  | Suppressed if `quiet`. (Moved from stdout to stderr.)                     |
| `error`    | stderr  | Always prints. (Moved from stdout to stderr.)                             |
| `debug`    | stderr  | Only prints if `debug` is set.                                            |

`error` and `warning` move to stderr because they belong on the diagnostic channel. This also unblocks `--json` output cleanliness on stdout.

The console used for stderr writes mirrors the theme of the stdout `console`. Because `_apply_theme` already rebuilds the stdout `console` on every theme change, the stderr console is rebuilt in the same place — `_apply_theme` constructs both `console` and `_stderr_console` so they always share a theme.

### 3. Wiring from `ClirApp`

`ClirApp._parse_global_flags` already computes the booleans. After parsing, it calls:

```python
from clir.runtime import set_verbosity, Verbosity
set_verbosity(Verbosity(self._quiet, self._verbose, self._debug))
```

No change to the parsing logic itself.

### 4. Error hierarchy (`clir/errors.py`)

```python
class ClirError(Exception):
    """Base class for framework-raised errors. message + exit_code."""
    exit_code: int = 1

    def __init__(self, message: str, *, exit_code: int | None = None):
        super().__init__(message)
        self.message = message
        if exit_code is not None:
            self.exit_code = exit_code

class UsageError(ClirError):
    """Bad CLI input from the user. Exit 2."""
    exit_code = 2
```

The existing `ConfigError` in `clir/config/__init__.py` is rebased to inherit from `ClirError`. `pydantic.ValidationError` is left alone — we only handle it in the dispatcher, not redefine it.

### 5. Centralized exception handler

The two `except Exception` sites in `core/app.py` (currently at lines ~348 and ~366) collapse into a single method:

```python
def _handle_exception(self, exc: BaseException) -> "NoReturn":
    from clir.runtime import get_verbosity
    from clir.output import error as print_error
    import traceback, sys

    if isinstance(exc, KeyboardInterrupt):
        print("Aborted.", file=sys.stderr)
        sys.exit(130)

    if isinstance(exc, ClirError):
        print_error(exc.message)
        sys.exit(exc.exit_code)

    if isinstance(exc, ValidationError):  # pydantic
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

The two existing `try/except` blocks (around `await cmd.run(...)` in `_run_command` and around `asyncio.run(group.run(...))` in `_run_group_command`) keep their location but their bodies become a single line: `self._handle_exception(exc)`. `_handle_exception` always calls `sys.exit(...)` and never returns, so the type signature uses `NoReturn`.

### 6. Cleanups

- Delete `clir/core/app.py:168` (unreachable `self._aliases = {}`).
- Delete the `--debug=` branch at `clir/core/app.py:138-140`. It forwards a flag argparse doesn't know about; if a user command has its own `--debug` option, the global parser already stops at the first positional and passes the rest through unchanged.

## Components and dependencies

| New / modified                        | Depends on                                  |
|---------------------------------------|---------------------------------------------|
| `clir/runtime.py` (new)               | stdlib only                                 |
| `clir/errors.py` (new)                | stdlib only                                 |
| `clir/output/style.py` (modified)     | `clir.runtime`                              |
| `clir/core/app.py` (modified)         | `clir.runtime`, `clir.errors`               |
| `clir/config/__init__.py` (modified)  | `clir.errors` (rebase `ConfigError`)        |
| `clir/__init__.py` (modified)         | exports `ClirError`, `UsageError`           |

`runtime.py` and `errors.py` have zero internal dependencies — they're leaf modules. `output/style.py` already imports from `clir.runtime` cleanly because `runtime` doesn't import any output code.

## Data flow

```
sys.argv -> ClirApp.run -> _parse_global_flags -> set_verbosity(...)
                                                       |
                                                       v
                                                ContextVar
                                                       ^
                                                       |
        success/info/warning/error/debug --> get_verbosity --> gate
                                                       |
                                                       v
                                                stdout / stderr
```

```
command coroutine raises -> _handle_exception(exc)
                                |
                                +-- ClirError       -> styled error, exit_code
                                +-- KeyboardInterrupt -> "Aborted.", 130
                                +-- ValidationError -> per-field errors, 2
                                +-- other           -> debug? traceback : short, 1
```

## Testing

New: `tests/test_verbosity.py`

- `--quiet` suppresses `success/info/warning`, lets `error/echo` through.
- `--debug` enables `debug()` output (default suppresses).
- No flag: `success/info/warning/error/echo` print; `debug` suppressed.
- `error` and `warning` go to stderr; `success/info/echo` go to stdout.
- ContextVar isolation: setting verbosity in one task doesn't leak into a sibling task.

New: `tests/test_errors.py`

- `UsageError` raised from a command exits with code 2 and prints styled message.
- `ClirError(..., exit_code=7)` exits 7.
- `KeyboardInterrupt` exits 130 with "Aborted." on stderr.
- Generic `RuntimeError` without `--debug`: short message, exit 1, no traceback.
- Same `RuntimeError` with `--debug`: traceback printed, exit 1.
- `pydantic.ValidationError`: per-field error lines, exit 2.

Existing tests in `test_cli.py`, `test_groups.py`, `test_output.py`, `test_prompts.py`, `test_edge_cases.py` should continue to pass unchanged. The output functions keep their signatures; only their gating and stream change.

## Risks and mitigations

- **`error`/`warning` moving to stderr** is the only observable behavior change for code that doesn't use the global flags. Mitigation: documented in the changelog; tests assert the new stream.
- **ContextVar default value** means uninitialized callers (e.g. unit tests that import `success` directly without going through `app.run`) see `Verbosity()` defaults — same as today's behavior.
- **`ConfigError` rebase**: existing `except ConfigError` callers continue to work because `ClirError` is also an `Exception`.

## Rollout

Single commit / single PR. No feature flag needed — these are correctness fixes.

## Out of scope (Phase 2)

- Unifying the rich `_print_help` and argparse-default help output across app/group/command levels.
- Splitting `ClirApp.run` into a sync entry + `async def run_async` so a single event loop covers all dispatch and async callers can `await` it.
