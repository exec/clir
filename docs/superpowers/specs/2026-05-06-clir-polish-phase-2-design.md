# Clir Polish — Phase 2: Help Unification + Asyncio Loop Sharing

**Date:** 2026-05-06
**Scope:** Phase 2 of the two-phase polish pass on `clir`. Phase 1 (verbosity wiring + error story) shipped in `feat/polish-phase-1`-equivalent commits on `main`.

## Motivation

Two structural inconsistencies remain after Phase 1:

1. **Two parallel help printers.** `ClirApp._print_help` is a hand-rolled rich-styled help block used for top-level `--help`, search, and no-args. But `mycli somegroup --help` and `mycli somecmd --help` go through argparse's default help output. The look-and-feel changes depending on which surface the user touches.
2. **Three `asyncio.run(...)` call sites.** `app.run` invokes `asyncio.run` at three places (default-command path, regular-command path, group-command path). Each creates a fresh event loop. Two consequences: `app.run()` cannot be invoked from an already-running loop (FastAPI startup, Jupyter, async tests), and per-command loop churn is wasteful.

Phase 2 collapses each into a single canonical implementation while keeping the public sync API intact.

## Non-goals

- New features, output components, or CLI flags.
- Backward-incompatible changes to `app.run` or the output API.
- Removing argparse — argparse keeps doing argument *parsing*; only its *help printing* is replaced.

## Design

### 1. Help unification (`clir/help.py`)

A new module with a single rich-styled renderer that handles app, group, and command levels uniformly:

```python
def render_help(
    target: ClirApp | Group | Command,
    *,
    app_name: str,
    parent_path: str = "",
    search: str | None = None,
) -> None: ...
```

`parent_path` is everything BEFORE the target's own name in the breadcrumb. For `target=app`, `parent_path=""`. For `target=group` named `db`, `parent_path=""` (group is top-level under app). For a sub-group `migrate` under `db`, `parent_path="db"`. For a `Command` named `up` under `db migrate`, `parent_path="db migrate"`. The renderer composes `Usage:` as `<app_name> [<parent_path>] <target.name> [options]`. `search` filters commands by name/help substring (current behavior of `_print_help`'s search query).

The renderer produces the same visual style currently used by `ClirApp._print_help` — bold headers, a rich `Table` with `cyan` command names and `dim` help text — across all three surfaces. It also renders an **Options** section listing every option/argument when called for a `Command`.

#### Wiring

- `ClirApp._print_help` becomes a thin wrapper: `render_help(self, app_name=self.name, search=search_query)`.
- `_run_group_command`'s `--help` branch (currently builds an argparse parser to print help and exit) becomes `render_help(group, app_name=self.name, parent_path=group.name); return`.
- Per-command `--help` is intercepted via a custom `argparse.Action`. We register `ClirHelpAction` on every parser built in `_populate_subparsers` and `_parse_args`. When triggered, the action calls `render_help(cmd, ...)` then `sys.exit(0)`. argparse's default `--help` is suppressed via `add_help=False` on those parsers.

#### Why a custom action and not pre-intercept

argparse already does the heavy parsing lift. Pre-intercepting `--help` in `argv` before argparse sees it would require us to reproduce argparse's command-name resolution (including subparsers). A custom `argparse.Action` plugs into argparse's flow without us re-implementing dispatch.

#### Tests

`tests/test_help.py` — three snapshot-style tests, one per surface (app, group, command). Each invokes `--help` via `CliRunner` and asserts:
- The `Usage:` line includes the right path.
- Each registered command/option appears.
- The styled-table marker (e.g., a known section header like `Commands:`) is present.

Not pixel-exact — substring assertions, so theme changes don't break tests.

### 2. Asyncio loop sharing (`run_async`)

Split `ClirApp.run` into a thin sync wrapper and an async core:

```python
def run(self, argv: list[str] | None = None) -> None:
    asyncio.run(self.run_async(argv))

async def run_async(self, argv: list[str] | None = None) -> None:
    # everything currently in `run`, but await-based
    ...
```

All dispatch logic — global flag parse, alias resolution, command/group lookup, help, error handling — moves into `run_async`. The three internal `asyncio.run(...)` calls collapse into plain `await`s. One event loop per invocation.

#### `_run_group_command` becomes async

The current sync `_run_group_command` calls `asyncio.run(group.run(...))`. After Phase 2 it's `async def _run_group_command` and `await group.run(...)`. Recursive calls to itself become `await`.

#### `_run_command` is already async

No change to its signature — it stays `async def _run_command(...)`. Its callers in `run_async` use `await` instead of `asyncio.run`.

#### What async callers gain

```python
# In an async test, FastAPI startup, Jupyter cell, etc.
await app.run_async(["cmd", "arg"])
```

No `RuntimeError: asyncio.run() cannot be called from a running event loop`.

#### What sync callers see

`CliRunner.invoke` and any user calling `app.run()` continue to work unchanged — the sync entry point still calls `asyncio.run` exactly once internally. No public API change.

#### Tests

`tests/test_async.py` — three cases:
- `await app.run_async(["cmd"])` from an async test executes the command and produces expected output.
- `await app.run_async(["group", "subcmd"])` works for nested groups.
- A command that raises propagates through `_handle_exception` correctly when invoked via `run_async`.

`pytest-asyncio` is already in dev-deps so `@pytest.mark.asyncio` is available.

## Components and dependencies

| New / modified                        | Depends on                                  |
|---------------------------------------|---------------------------------------------|
| `clir/help.py` (new)                  | `clir.core.command`, `clir.core.group`, `rich.Console`, `rich.Table` |
| `clir/core/app.py` (modified)         | `clir.help` (for `render_help`); structural rework of `run` → `run_async` |
| `tests/test_help.py` (new)            | `clir.testing.CliRunner`                    |
| `tests/test_async.py` (new)           | `pytest-asyncio`, `clir.testing.CliRunner`  |

`clir/help.py` is a leaf in terms of internal deps — it imports core types but nothing imports it back outside `app.py`.

## Data flow

### Help (after Phase 2)

```
mycli --help              -> ClirApp._print_help -> render_help(app)
mycli somegroup --help    -> _run_group_command  -> render_help(group, parent_path="somegroup")
mycli somecmd --help      -> argparse parses     -> ClirHelpAction triggers -> render_help(cmd, parent_path="somecmd")
```

### Async (after Phase 2)

```
sync caller  -> app.run(argv)   -> asyncio.run(app.run_async(argv))
async caller -> await app.run_async(argv)
                                   |
                                   +-- await self._run_command(cmd, parsed)
                                   |     await cmd.run(args)
                                   |
                                   +-- await self._run_group_command(group, argv)
                                         await group.run(parsed)
```

One event loop per `run_async` invocation. ContextVar verbosity (Phase 1) propagates naturally across `await` boundaries within that loop.

## Testing

New: `tests/test_help.py`

- `test_app_help_lists_commands` — `mycli --help` includes `Commands:` and each registered command name.
- `test_group_help_lists_subcommands` — `mycli somegroup --help` includes the group's subcommands and the breadcrumb in `Usage:`.
- `test_command_help_lists_options` — `mycli somecmd --help` includes `Options:` and each registered option's flag.
- `test_help_search_filters_commands` — `mycli --search foo --help` (or equivalent) includes only commands matching `foo`.
- `test_help_via_argparse_action_for_command` — verify `--help` after a command name routes through `render_help`, not argparse's default.

New: `tests/test_async.py`

- `test_run_async_executes_command` — `await app.run_async(["cmd"])` runs the command and produces output.
- `test_run_async_handles_groups` — `await app.run_async(["g", "sub"])` works.
- `test_run_async_propagates_errors` — when a command raises, `_handle_exception` runs and `SystemExit` propagates correctly.
- `test_sync_run_still_works` — `app.run(["cmd"])` (sync entry) keeps existing behavior; full suite catches this implicitly but an explicit test makes the contract obvious.

Existing tests in `test_cli.py`, `test_groups.py`, `test_output.py`, `test_prompts.py`, `test_edge_cases.py`, `test_verbosity.py`, and `test_errors.py` should pass unchanged. Specifically:
- `test_groups.py` exercises `_run_group_command` heavily; the async conversion must not break it.
- `test_cli.py`'s `--help` assertions (if any) must still match the new rich-styled output (substring-level, not pixel).

## Risks and mitigations

- **argparse's `add_help=False`** disables its built-in `--help`. We must register `ClirHelpAction` on EVERY parser we build (top-level, group, sub-command). Forgetting one means that surface silently falls back to "no help available." Mitigation: a single helper `_make_parser(...)` that always installs `ClirHelpAction`; tests cover all three surfaces. `ClirHelpAction` always calls `sys.exit(0)` after rendering — `CliRunner.invoke` catches `SystemExit` and returns `exit_code=0`, so existing test harnesses keep working.
- **Async conversion of `_run_group_command`** is the biggest functional change. Recursive calls and the help-printing branch both need conversion. Mitigation: the existing `test_groups.py` (with nested-group tests) is the regression net.
- **Test isolation under `pytest-asyncio`.** The ContextVar verbosity from Phase 1 is per-task; pytest-asyncio creates a fresh task per test. Should be safe, but verify with one explicit test that doesn't reset verbosity at entry.
- **Backward compat for users who already wrote `app.run()`.** Unchanged — sync wrapper preserves behavior. `CliRunner.invoke` continues to call `app.run`.

## Rollout

Single PR atop the Phase 1 commits. Two logical commits within it:
1. Help unification (`clir/help.py` + wiring + tests).
2. `run_async` split (refactor `run` → `run_async`, async-ify `_run_group_command`, tests).

In that order — help unification is independent of the async work, so it lands first on a stable base. Async refactor doesn't touch help logic.

## Out of scope (for any future phase)

- Replacing argparse entirely with a hand-rolled parser.
- Real Ctrl+C signal handling inside async commands (currently `_handle_exception` covers programmatic `KeyboardInterrupt`; SIGINT from the terminal during `await` is a separate concern).
- An `await runner.invoke_async(...)` test helper. Not needed unless test patterns require it.
