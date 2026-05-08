# Clir Polish Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the three help-output paths (app/group/command) under one rich-styled renderer, and split `ClirApp.run` into a sync entry + `async def run_async` so a single event loop covers all dispatch and async callers can `await` the app.

**Architecture:** New `clir/help.py` exports `render_help(target, *, app_name, parent_path, search)` that dispatches on target type (`ClirApp` | `Group` | `Command`) and emits a rich `Table` with shared visual style. `ClirApp._print_help` and `_run_group_command`'s `--help` branch route through it. Per-command `--help` is intercepted by a custom `ClirHelpAction` registered on every argparse parser (with `add_help=False` to disable argparse's built-in). For async, `app.run` becomes `asyncio.run(self.run_async(argv))`; all dispatch logic moves into `run_async`; `_run_group_command` becomes `async def` and the three internal `asyncio.run(...)` sites collapse into `await`s. ContextVar verbosity from Phase 1 propagates naturally across `await` boundaries.

**Tech Stack:** Python 3.10+, `rich.Console` + `rich.Table` for help rendering, `argparse` for parsing only (custom `Action` for help). `pytest-asyncio` (already in dev deps) for async tests.

**Spec:** `docs/superpowers/specs/2026-05-06-clir-polish-phase-2-design.md`

---

## File Structure

| Action  | Path                                | Responsibility                                                                  |
|---------|-------------------------------------|---------------------------------------------------------------------------------|
| Create  | `clir/help.py`                      | `render_help(target, ...)` dispatching on `ClirApp`/`Group`/`Command`.          |
| Modify  | `clir/core/app.py`                  | (a) `_print_help` → wrapper; (b) `_run_group_command` `--help` branch → `render_help`; (c) `ClirHelpAction` registered on every parser; (d) `run` → sync wrapper, all logic in new `run_async`; (e) `_run_group_command` becomes `async def`. |
| Create  | `tests/test_help.py`                | Tests for app/group/command `--help` and search.                                |
| Create  | `tests/test_async.py`               | Tests for `await app.run_async(...)` + sync compatibility.                      |

`clir/help.py` is a near-leaf module: imports rich + the core types but is not imported by any module other than `clir.core.app`.

---

## Task 0: Pre-flight

**Files:** none

- [ ] **Step 1: Verify branch state and tests**

```bash
cd /Users/dylan/Developer/clir
source .venv/bin/activate
git log --oneline | head -3
python -m pytest tests/ -q
```

Expected: HEAD is `560f91a feat(clir): re-export ClirError and UsageError` (last commit of Phase 1), 108/108 tests pass.

- [ ] **Step 2: Capture base SHA**

```bash
git rev-parse HEAD
```

Record this as `BASE_SHA` for Phase 2; the per-task subagent reviews will use it as the diff base.

---

## Task 1: `render_help` for ClirApp target

**Files:**
- Create: `clir/help.py`
- Test:   `tests/test_help.py`

This task lays the renderer's skeleton with only `ClirApp`-target support. Group and Command branches come in tasks 2 and 3.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_help.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_help.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clir.help'`.

- [ ] **Step 3: Implement `clir/help.py` (ClirApp target only)**

Create `clir/help.py`:

```python
"""Unified help-output rendering for clir applications.

Exposes a single `render_help(target, *, app_name, parent_path, search)` that
handles ClirApp, Group, and Command targets with consistent visual style.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

from clir.output.style import get_console

if TYPE_CHECKING:
    from clir.core.app import ClirApp
    from clir.core.command import Command
    from clir.core.group import Group


def render_help(
    target: "ClirApp | Group | Command",
    *,
    app_name: str,
    parent_path: str = "",
    search: str | None = None,
) -> None:
    """Render help for the given target to the stdout console.

    parent_path is everything before the target's own name in the breadcrumb.
    For target=app, parent_path="". For target=group at top level,
    parent_path="". For a command under a group named "db",
    parent_path="db".
    """
    # Lazy imports to avoid a cycle (clir.help is imported from app.py)
    from clir.core.app import ClirApp

    if isinstance(target, ClirApp):
        _render_app(target, app_name=app_name, search=search)
        return

    raise NotImplementedError(
        f"render_help does not yet support target type {type(target).__name__}"
    )


def _render_app(app: "ClirApp", *, app_name: str, search: str | None) -> None:
    console = get_console()
    console.print(f"[bold]Usage:[/bold] {app_name} [command] [options]")
    console.print()

    if app.description:
        console.print(app.description)
        console.print()

    commands = app.commands
    if search:
        q = search.lower()
        commands = {
            name: cmd
            for name, cmd in commands.items()
            if q in name.lower() or (cmd.help and q in cmd.help.lower())
        }
        if not commands:
            console.print(f"[yellow]No commands found matching '{search}'[/yellow]")
            console.print()
            return

    if commands:
        console.print("[bold]Commands:[/bold]")
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("name", style="cyan")
        table.add_column("help", style="dim")
        for name, cmd in commands.items():
            table.add_row(f"  {name}", cmd.help or "")
        console.print(table)
        console.print()
        console.print(f"Run '{app_name} <command> --help' for more info on a command.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_help.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Run full suite for regressions**

Run: `python -m pytest tests/ -q`
Expected: 111 PASS (108 + 3 new).

- [ ] **Step 6: Commit**

```bash
git add clir/help.py tests/test_help.py
git commit -m "feat(help): add render_help skeleton with ClirApp target"
```

---

## Task 2: `render_help` for Group target

**Files:**
- Modify: `clir/help.py`
- Test:   `tests/test_help.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_help.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_help.py -v -k group`
Expected: FAIL — `render_help` raises `NotImplementedError` for Group target.

- [ ] **Step 3: Add the Group branch to `render_help`**

In `clir/help.py`, replace this section:

```python
    if isinstance(target, ClirApp):
        _render_app(target, app_name=app_name, search=search)
        return

    raise NotImplementedError(
        f"render_help does not yet support target type {type(target).__name__}"
    )
```

with:

```python
    from clir.core.group import Group

    if isinstance(target, ClirApp):
        _render_app(target, app_name=app_name, search=search)
        return

    if isinstance(target, Group):
        _render_group(target, app_name=app_name, parent_path=parent_path)
        return

    raise NotImplementedError(
        f"render_help does not yet support target type {type(target).__name__}"
    )
```

(Note: `Group` MUST be checked before `Command` in any future task because `Group` inherits from `Command`.)

Add this helper function below `_render_app` in `clir/help.py`:

```python
def _render_group(group: "Group", *, app_name: str, parent_path: str) -> None:
    console = get_console()
    breadcrumb = " ".join(p for p in (app_name, parent_path, group.name) if p)
    console.print(f"[bold]Usage:[/bold] {breadcrumb} [command] [options]")
    console.print()

    if group.help:
        console.print(group.help)
        console.print()

    if group.commands:
        console.print("[bold]Commands:[/bold]")
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("name", style="cyan")
        table.add_column("help", style="dim")
        for name, cmd in group.commands.items():
            table.add_row(f"  {name}", cmd.help or "")
        console.print(table)
        console.print()
        console.print(f"Run '{breadcrumb} <command> --help' for more info on a command.")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_help.py -v`
Expected: all 5 PASS (3 from Task 1 + 2 new).

- [ ] **Step 5: Run full suite**

Run: `python -m pytest tests/ -q`
Expected: 113 PASS.

- [ ] **Step 6: Commit**

```bash
git add clir/help.py tests/test_help.py
git commit -m "feat(help): add render_help support for Group target"
```

---

## Task 3: `render_help` for Command target (with options listing)

**Files:**
- Modify: `clir/help.py`
- Test:   `tests/test_help.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_help.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_help.py -v -k command_help`
Expected: FAIL — `render_help` raises `NotImplementedError` for Command target.

- [ ] **Step 3: Add the Command branch to `render_help`**

In `clir/help.py`, replace this dispatch:

```python
    from clir.core.group import Group

    if isinstance(target, ClirApp):
        _render_app(target, app_name=app_name, search=search)
        return

    if isinstance(target, Group):
        _render_group(target, app_name=app_name, parent_path=parent_path)
        return

    raise NotImplementedError(
        f"render_help does not yet support target type {type(target).__name__}"
    )
```

with:

```python
    from clir.core.command import Command
    from clir.core.group import Group

    if isinstance(target, ClirApp):
        _render_app(target, app_name=app_name, search=search)
        return

    # Group MUST be checked before Command — Group is a subclass of Command.
    if isinstance(target, Group):
        _render_group(target, app_name=app_name, parent_path=parent_path)
        return

    if isinstance(target, Command):
        _render_command(target, app_name=app_name, parent_path=parent_path)
        return

    raise NotImplementedError(
        f"render_help does not yet support target type {type(target).__name__}"
    )
```

Add this helper function below `_render_group`:

```python
def _render_command(cmd: "Command", *, app_name: str, parent_path: str) -> None:
    console = get_console()
    breadcrumb = " ".join(p for p in (app_name, parent_path, cmd.name) if p)

    args = [p for p in cmd.params if p.param_type.value == "argument"]
    opts = [p for p in cmd.params if p.param_type.value == "option"]

    arg_summary = " ".join(f"<{p.name}>" for p in args)
    opts_summary = "[options]" if opts else ""
    parts = [breadcrumb, arg_summary, opts_summary]
    usage_line = " ".join(p for p in parts if p)
    console.print(f"[bold]Usage:[/bold] {usage_line}")
    console.print()

    if cmd.help:
        console.print(cmd.help)
        console.print()

    if args:
        console.print("[bold]Arguments:[/bold]")
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("name", style="cyan")
        table.add_column("help", style="dim")
        for p in args:
            table.add_row(f"  {p.name}", p.help or "")
        console.print(table)
        console.print()

    if opts:
        console.print("[bold]Options:[/bold]")
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("name", style="cyan")
        table.add_column("help", style="dim")
        for p in opts:
            flag = f"--{p.name.replace('_', '-')}"
            if p.short:
                flag = f"{p.short.lstrip('-')}, {flag}" if not p.short.startswith("-") else f"{p.short}, {flag}"
            table.add_row(f"  {flag}", p.help or "")
        console.print(table)
        console.print()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_help.py -v`
Expected: all 8 PASS.

- [ ] **Step 5: Run full suite**

Run: `python -m pytest tests/ -q`
Expected: 116 PASS.

- [ ] **Step 6: Commit**

```bash
git add clir/help.py tests/test_help.py
git commit -m "feat(help): add render_help support for Command target with options"
```

---

## Task 4: Wire `ClirApp._print_help` to `render_help`

**Files:**
- Modify: `clir/core/app.py:546-589`
- Test:   `tests/test_help.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_help.py`:

```python
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
```

These tests already pass with the OLD `_print_help` implementation (which produces similar substrings). The change in Task 4 is to swap the implementation under the hood while preserving these substrings. The tests serve as a regression guard.

- [ ] **Step 2: Run tests to verify current behavior matches**

Run: `python -m pytest tests/test_help.py -v -k "print_help or search_query"`
Expected: 2 PASS (existing behavior already matches).

- [ ] **Step 3: Replace `ClirApp._print_help`**

In `clir/core/app.py`, replace the entire `_print_help` method (currently lines 546-589):

```python
    def _print_help(self, search_query: str | None = None) -> None:
        """Print help message.

        Args:
            search_query: Optional search term to filter commands
        """
        from rich.console import Console
        from rich.table import Table

        console = Console()
        console.print(f"[bold]Usage:[/bold] {self.name} [command] [options]")
        console.print()

        if self.description:
            console.print(self.description)
            console.print()

        if self.commands:
            # Filter commands if search_query is provided
            filtered_commands = self.commands
            if search_query:
                query = search_query.lower()
                filtered_commands = {
                    name: cmd for name, cmd in self.commands.items()
                    if query in name.lower() or (cmd.help and query in cmd.help.lower())
                }

            if filtered_commands:
                console.print("[bold]Commands:[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 1))
                table.add_column("name", style="cyan")
                table.add_column("help", style="dim")

                for name, cmd in filtered_commands.items():
                    table.add_row(f"  {name}", cmd.help or "")

                console.print(table)
                console.print()

            if search_query and not filtered_commands:
                console.print(f"[yellow]No commands found matching '{search_query}'[/yellow]")
                console.print()

            console.print(f"Run '{self.name} <command> --help' for more info on a command.")
```

with:

```python
    def _print_help(self, search_query: str | None = None) -> None:
        """Print help message via the unified render_help renderer."""
        from clir.help import render_help
        render_help(self, app_name=self.name, search=search_query)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_help.py -v`
Expected: all 10 PASS.

- [ ] **Step 5: Run full suite**

Run: `python -m pytest tests/ -q`
Expected: 118 PASS (116 + 2 new).

- [ ] **Step 6: Commit**

```bash
git add clir/core/app.py tests/test_help.py
git commit -m "refactor(app): route _print_help through render_help"
```

---

## Task 5: Wire group `--help` through `render_help`

**Files:**
- Modify: `clir/core/app.py:300-316` (the `--help` branch of `_run_group_command`)
- Test:   `tests/test_help.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_help.py`:

```python
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
```

- [ ] **Step 2: Run test to verify the current argparse output is different**

Run: `python -m pytest tests/test_help.py::test_group_help_via_cli_runner_uses_render_help -v`
Expected: This MAY pass or fail with the current argparse default (argparse output mentions "myapp db" and the subcommands but in a different format). Run it; if it passes already, the change in Step 3 is still required to unify visual style. Either way, proceed to Step 3.

- [ ] **Step 3: Replace the `--help` branch in `_run_group_command`**

In `clir/core/app.py`, find the `_run_group_command` method (currently around line 300). Replace the `--help` branch (currently lines 307-316):

```python
        # Check for --help
        if "--help" in argv or "-h" in argv:
            # Show help for this group
            group_parser = argparse.ArgumentParser(
                prog=f"{self.name} {group.name}",
                description=group.help,
            )
            self._populate_subparsers(group_parser, group.commands)
            group_parser.parse_args(argv)  # This will print help and exit
            return
```

with:

```python
        # Check for --help
        if "--help" in argv or "-h" in argv:
            from clir.help import render_help
            render_help(group, app_name=self.name, parent_path="")
            return
```

(For nested groups, `parent_path` should accumulate. The current `_run_group_command` recursion does not pass through a parent_path; we leave it as `""` for now — nested-group `--help` paths are an edge case not currently exercised by tests. If needed in a follow-up, thread a `parent_path` argument through `_run_group_command`.)

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_help.py -v`
Expected: all 11 PASS.

- [ ] **Step 5: Run full suite, paying attention to `tests/test_groups.py`**

Run: `python -m pytest tests/ -q`
Expected: 119 PASS.

If `test_groups.py` regresses, inspect: did any test assert exact argparse-default help output (e.g., "usage: " lowercase or specific argparse formatting)? Update those asserts to match the rich-styled output. Show me what changed.

- [ ] **Step 6: Commit**

```bash
git add clir/core/app.py tests/test_help.py tests/test_groups.py
git commit -m "refactor(app): route group --help through render_help"
```

(Adjust the staged file list if no test_groups.py change was needed.)

---

## Task 6: `ClirHelpAction` for per-command `--help`

**Files:**
- Modify: `clir/core/app.py` (add `ClirHelpAction` class; add `add_help=False` + `ClirHelpAction` registration to every parser construction site)
- Test:   `tests/test_help.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_help.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail or behave inconsistently**

Run: `python -m pytest tests/test_help.py -v -k "command_help_via_cli_runner or subcommand_under_group"`
Expected: FAIL — argparse's default `--help` output doesn't match the new `render_help` markers.

- [ ] **Step 3: Add `ClirHelpAction`**

In `clir/core/app.py`, add this class (place it right after the imports, before `class ClirApp`):

```python
class ClirHelpAction(argparse.Action):
    """Custom argparse Action that routes --help through render_help and exits.

    Replaces argparse's built-in -h/--help so that all help surfaces use the
    same rich-styled renderer.
    """

    def __init__(
        self,
        option_strings: list[str],
        dest: str = argparse.SUPPRESS,
        default: object = argparse.SUPPRESS,
        help: str | None = None,
        *,
        app_name: str,
        target: object,
        parent_path: str = "",
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )
        self._app_name = app_name
        self._target = target
        self._parent_path = parent_path

    def __call__(self, parser, namespace, values, option_string=None):
        from clir.help import render_help
        render_help(self._target, app_name=self._app_name, parent_path=self._parent_path)
        import sys
        sys.exit(0)
```

- [ ] **Step 4: Update `_populate_subparsers` to register `ClirHelpAction` on each sub-parser**

In `clir/core/app.py`, replace the existing `_populate_subparsers` method (currently lines 457-480):

```python
    def _populate_subparsers(
        self,
        parser: argparse.ArgumentParser,
        commands: dict[str, "Command | Group"],
        dest: str = "subcommand",
    ) -> None:
        """Add subparsers to parser for the given commands, recursing into Groups.

        Args:
            parser: The argparse parser to add subparsers to
            commands: Dict of command name → Command or Group
            dest: The argparse dest attribute for the subparser selector
        """
        if not commands:
            return

        subparsers = parser.add_subparsers(dest=dest)

        for cmd_name, cmd in commands.items():
            sub = subparsers.add_parser(cmd_name, help=cmd.help)
            if isinstance(cmd, Group):
                self._populate_subparsers(sub, cmd.commands)
            else:
                self._add_command_params(sub, cmd, reverse_args=True)
```

with:

```python
    def _populate_subparsers(
        self,
        parser: argparse.ArgumentParser,
        commands: dict[str, "Command | Group"],
        dest: str = "subcommand",
        parent_path: str = "",
    ) -> None:
        """Add subparsers to parser for the given commands, recursing into Groups.

        Each sub-parser has argparse's built-in --help disabled and a
        ClirHelpAction registered instead, so --help renders via render_help.
        """
        if not commands:
            return

        subparsers = parser.add_subparsers(dest=dest)

        for cmd_name, cmd in commands.items():
            sub = subparsers.add_parser(cmd_name, help=cmd.help, add_help=False)
            sub.add_argument(
                "-h", "--help",
                action=ClirHelpAction,
                app_name=self.name,
                target=cmd,
                parent_path=parent_path,
            )
            if isinstance(cmd, Group):
                child_path = f"{parent_path} {cmd_name}".strip()
                self._populate_subparsers(sub, cmd.commands, parent_path=child_path)
            else:
                self._add_command_params(sub, cmd, reverse_args=True)
```

- [ ] **Step 5: Update `_parse_args` to disable argparse's default help on the top-level parser**

In `clir/core/app.py`, replace the existing `_parse_args` method (currently around lines 482-489):

```python
    def _parse_args(self, argv: list[str]) -> dict[str, Any]:
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
        )
        self._populate_subparsers(parser, self.commands, dest="command")
        return vars(parser.parse_args(argv))
```

with:

```python
    def _parse_args(self, argv: list[str]) -> dict[str, Any]:
        """Parse command-line arguments.

        The top-level parser's --help is intercepted earlier in `run`
        (it short-circuits to render_help before reaching here), so we
        disable argparse's built-in help on the top-level parser too —
        otherwise an unrecognized --help between command names would
        trigger argparse's default formatter.
        """
        parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
            add_help=False,
        )
        self._populate_subparsers(parser, self.commands, dest="command")
        return vars(parser.parse_args(argv))
```

- [ ] **Step 6: Update `_run_group_command`'s inline parser construction**

In `clir/core/app.py`, find `_run_group_command` (currently around line 300). Replace the second `argparse.ArgumentParser` construction (currently lines 338-342):

```python
            # Regular command under this group
            # Create parser for this group's subcommands
            group_parser = argparse.ArgumentParser(
                prog=f"{self.name} {group.name}",
                description=group.help,
            )
            self._populate_subparsers(group_parser, group.commands)
```

with:

```python
            # Regular command under this group
            # Create parser for this group's subcommands
            group_parser = argparse.ArgumentParser(
                prog=f"{self.name} {group.name}",
                description=group.help,
                add_help=False,
            )
            self._populate_subparsers(group_parser, group.commands, parent_path=group.name)
```

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/test_help.py -v`
Expected: all 13 PASS.

- [ ] **Step 8: Run full suite, watching `tests/test_groups.py` and `tests/test_cli.py`**

Run: `python -m pytest tests/ -q`
Expected: 121 PASS.

If a test regresses asserting on argparse-default `--help` output, update the assertion to match the new rich-styled output (substring level — don't pixel-match). Show me what changed.

- [ ] **Step 9: Commit**

```bash
git add clir/core/app.py tests/test_help.py
# Add any updated test files if you had to fix regressions:
# git add tests/test_groups.py tests/test_cli.py
git commit -m "refactor(app): route per-command --help through ClirHelpAction"
```

---

## Task 7: Split `run` into sync wrapper + `async def run_async` AND convert `_run_group_command` to async

**Files:**
- Modify: `clir/core/app.py` (`run` method body around lines 229-298 AND `_run_group_command` around lines 300-348)
- Test:   `tests/test_async.py`

This task does the entire async refactor in one shot: move dispatch logic from `run` into new `async def run_async`, convert `_run_group_command` from sync to async, and replace all three `asyncio.run(...)` call sites with single-loop `await`s. Doing both at once avoids a temporary nested-loop regression that would occur if `run` wrapped `run_async` while `_run_group_command` still called `asyncio.run` internally.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_async.py`:

```python
"""Tests for ClirApp.run_async — async-callable entry point."""

import asyncio
import pytest

from clir import ClirApp
from clir.errors import ClirError


@pytest.mark.asyncio
async def test_run_async_executes_command():
    app = ClirApp(name="myapp")
    out = []

    @app.command()
    def hello():
        out.append("ran")

    await app.run_async(["hello"])
    assert out == ["ran"]


@pytest.mark.asyncio
async def test_run_async_returns_none_for_help_short_circuit():
    app = ClirApp(name="myapp")

    @app.command()
    def hello():
        pass

    # Top-level --help renders help and returns (no sys.exit).
    result = await app.run_async(["--help"])
    assert result is None


@pytest.mark.asyncio
async def test_run_async_default_command():
    app = ClirApp(name="myapp")
    seen = []

    @app.command()
    def main():
        seen.append("default")

    app.default(app.commands["main"])
    await app.run_async([])
    assert seen == ["default"]


@pytest.mark.asyncio
async def test_run_async_executes_group_command():
    app = ClirApp(name="myapp")
    out = []

    @app.group()
    def db():
        """DB."""
        pass

    @db.command()
    def migrate():
        out.append("migrated")

    await app.run_async(["db", "migrate"])
    assert out == ["migrated"]


@pytest.mark.asyncio
async def test_run_async_executes_nested_group_command():
    app = ClirApp(name="myapp")
    out = []

    @app.group()
    def outer():
        pass

    @outer.group()
    def inner():
        pass

    @inner.command()
    def deep():
        out.append("deep")

    await app.run_async(["outer", "inner", "deep"])
    assert out == ["deep"]


@pytest.mark.asyncio
async def test_run_async_propagates_command_error():
    app = ClirApp(name="myapp")

    @app.command()
    def boom():
        raise ClirError("user-facing", exit_code=42)

    with pytest.raises(SystemExit) as exc_info:
        await app.run_async(["boom"])
    assert exc_info.value.code == 42


def test_sync_run_still_works():
    app = ClirApp(name="myapp")
    seen = []

    @app.command()
    def hello():
        seen.append("ran")

    app.run(["hello"])
    assert seen == ["ran"]


def test_sync_run_still_works_for_groups():
    app = ClirApp(name="myapp")
    out = []

    @app.group()
    def db():
        pass

    @db.command()
    def migrate():
        out.append("migrated")

    app.run(["db", "migrate"])
    assert out == ["migrated"]
```

`pytest-asyncio` may need a config tweak; if `pytest.mark.asyncio` is not picked up automatically, add this to `pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
asyncio_mode = "auto"
```

If you add the toml change, include `pyproject.toml` in the commit.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_async.py -v`
Expected: FAIL — `run_async` does not exist; calls raise `AttributeError`.

- [ ] **Step 3: Add `run_async`, reduce `run` to a sync wrapper, AND convert `_run_group_command` to async**

In `clir/core/app.py`, replace the existing `run` method (currently lines 229-298):

```python
    def run(self, argv: list[str] | None = None) -> None:
        """Run the CLI application."""
        # Use sys.argv[1:] only when argv is None, not when it's an empty list
        if argv is None:
            argv = sys.argv[1:]

        # Parse global flags
        argv = self._parse_global_flags(argv)

        # Handle --version before parsing
        if "--version" in argv:
            if self.version:
                print(f"{self.name} {self.version}")
            else:
                print(f"{self.name} (no version set)")
            return

        if not argv and self._default_command:
            # Run default command with no args
            asyncio.run(self._run_command(self._default_command, {}))
            return

        if not argv:
            self._print_help()
            return

        # Check for --search flag (with or without --help)
        if self._search:
            self._print_help(self._search)
            return

        # Check for --help at app level
        if argv[0] in ("--help", "-h"):
            self._print_help()
            return

        # Check if first arg is a known command/group
        first_arg = argv[0]

        # Resolve aliases
        resolved_arg = first_arg
        if self._alias_manager:
            resolved = self._alias_manager.resolve(first_arg)
            if resolved:
                # Split resolved command into parts
                parts = resolved.split()
                resolved_arg = parts[0]
                # Prepend remaining parts to argv
                argv = parts[1:] + argv[1:]

        cmd = self.commands.get(resolved_arg)

        if cmd:
            if isinstance(cmd, Group):
                # This is a group - recursively parse nested subcommands
                self._run_group_command(cmd, argv[1:])
            else:
                # Regular command
                parsed = self._parse_args(argv)
                parsed.pop("command", None)
                asyncio.run(self._run_command(cmd, parsed, parent=None))
        else:
            # Check for typo suggestion
            suggestion = self._suggest_command(first_arg)
            error_msg = f"Error: Unknown command '{first_arg}'"
            if suggestion:
                error_msg += f". Did you mean '{suggestion}'?"
            print(error_msg, file=sys.stderr)
            self._print_help()
            sys.exit(1)
```

with:

```python
    def run(self, argv: list[str] | None = None) -> None:
        """Run the CLI application synchronously.

        Thin wrapper around run_async. Async callers should use run_async
        directly to avoid the asyncio.run() loop creation.
        """
        asyncio.run(self.run_async(argv))

    async def run_async(self, argv: list[str] | None = None) -> None:
        """Run the CLI application asynchronously.

        All dispatch logic lives here; ClirApp.run wraps this in asyncio.run.
        """
        # Use sys.argv[1:] only when argv is None, not when it's an empty list
        if argv is None:
            argv = sys.argv[1:]

        # Parse global flags
        argv = self._parse_global_flags(argv)

        # Handle --version before parsing
        if "--version" in argv:
            if self.version:
                print(f"{self.name} {self.version}")
            else:
                print(f"{self.name} (no version set)")
            return

        if not argv and self._default_command:
            await self._run_command(self._default_command, {})
            return

        if not argv:
            self._print_help()
            return

        # Check for --search flag (with or without --help)
        if self._search:
            self._print_help(self._search)
            return

        # Check for --help at app level
        if argv[0] in ("--help", "-h"):
            self._print_help()
            return

        # Check if first arg is a known command/group
        first_arg = argv[0]

        # Resolve aliases
        resolved_arg = first_arg
        if self._alias_manager:
            resolved = self._alias_manager.resolve(first_arg)
            if resolved:
                parts = resolved.split()
                resolved_arg = parts[0]
                argv = parts[1:] + argv[1:]

        cmd = self.commands.get(resolved_arg)

        if cmd:
            if isinstance(cmd, Group):
                await self._run_group_command(cmd, argv[1:])
            else:
                parsed = self._parse_args(argv)
                parsed.pop("command", None)
                await self._run_command(cmd, parsed, parent=None)
        else:
            suggestion = self._suggest_command(first_arg)
            error_msg = f"Error: Unknown command '{first_arg}'"
            if suggestion:
                error_msg += f". Did you mean '{suggestion}'?"
            print(error_msg, file=sys.stderr)
            self._print_help()
            sys.exit(1)
```

Then in the same file, replace the existing `_run_group_command` method (currently around lines 300-348):

```python
    def _run_group_command(self, group: Group, argv: list[str]) -> None:
        """Recursively run a group command, handling nested groups.

        Args:
            group: The group to run
            argv: Remaining command-line arguments after the group name
        """
        # Check for --help
        if "--help" in argv or "-h" in argv:
            from clir.help import render_help
            render_help(group, app_name=self.name, parent_path="")
            return

        if not argv:
            # No more args, show help for this group
            print(f"Run '{self.name} {group.name} --help' for available commands.", file=sys.stderr)
            sys.exit(1)

        # Look up the next arg as a subcommand within this group
        subcommand_name = argv[0]
        subcmd = group.commands.get(subcommand_name)

        if not subcmd:
            print(f"Error: Unknown command '{subcommand_name}'", file=sys.stderr)
            print(f"Run '{self.name} {group.name} --help' for available commands.")
            sys.exit(1)

        if isinstance(subcmd, Group):
            # Nested group - recursively handle
            self._run_group_command(subcmd, argv[1:])
        else:
            # Regular command under this group
            # Create parser for this group's subcommands
            group_parser = argparse.ArgumentParser(
                prog=f"{self.name} {group.name}",
                description=group.help,
                add_help=False,
            )
            self._populate_subparsers(group_parser, group.commands, parent_path=group.name)

            parsed = vars(group_parser.parse_args(argv))
            try:
                asyncio.run(group.run(parsed, parent=None))
            except (Exception, KeyboardInterrupt) as e:
                self._handle_exception(e)
```

with:

```python
    async def _run_group_command(self, group: Group, argv: list[str]) -> None:
        """Recursively run a group command, handling nested groups.

        Args:
            group: The group to run
            argv: Remaining command-line arguments after the group name
        """
        # Check for --help
        if "--help" in argv or "-h" in argv:
            from clir.help import render_help
            render_help(group, app_name=self.name, parent_path="")
            return

        if not argv:
            print(f"Run '{self.name} {group.name} --help' for available commands.", file=sys.stderr)
            sys.exit(1)

        subcommand_name = argv[0]
        subcmd = group.commands.get(subcommand_name)

        if not subcmd:
            print(f"Error: Unknown command '{subcommand_name}'", file=sys.stderr)
            print(f"Run '{self.name} {group.name} --help' for available commands.")
            sys.exit(1)

        if isinstance(subcmd, Group):
            await self._run_group_command(subcmd, argv[1:])
        else:
            group_parser = argparse.ArgumentParser(
                prog=f"{self.name} {group.name}",
                description=group.help,
                add_help=False,
            )
            self._populate_subparsers(group_parser, group.commands, parent_path=group.name)

            parsed = vars(group_parser.parse_args(argv))
            try:
                await group.run(parsed, parent=None)
            except (Exception, KeyboardInterrupt) as e:
                self._handle_exception(e)
```

(The `run_async` shown in this same Step 3 already calls `await self._run_group_command(cmd, argv[1:])`, so no further call-site fix is needed.)

- [ ] **Step 4: Run async tests**

Run: `python -m pytest tests/test_async.py -v`
Expected: all 8 PASS.

- [ ] **Step 5: Run full suite, paying attention to `tests/test_groups.py`**

Run: `python -m pytest tests/ -q`
Expected: 129 PASS (121 + 8 new).

`tests/test_groups.py` exercises the sync path heavily (via `CliRunner.invoke` which calls `app.run`). Since `app.run` still wraps `run_async` via `asyncio.run`, all sync-path group tests should continue to pass unchanged. If anything regresses, inspect the failure carefully — likely a missed `await` or a stale sync helper — before patching.

- [ ] **Step 6: Commit**

```bash
git add clir/core/app.py tests/test_async.py
# If you modified pyproject.toml for asyncio_mode:
# git add pyproject.toml
git commit -m "feat(app): split run into sync wrapper + async run_async, share event loop"
```

---

## Task 8: Final integration smoke + cleanup

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite one last time**

Run: `python -m pytest tests/ -v`
Expected: 129 PASS, no failures.

- [ ] **Step 2: Manual smoke test of help and async**

```bash
cd examples
python taskman.py --help
python taskman.py list --help
python -c "
import asyncio
from taskman import app
asyncio.run(app.run_async(['list']))
"
```

Expected: Each `--help` output uses the rich-styled renderer (not argparse default). The async invocation runs the command without a `RuntimeError`.

- [ ] **Step 3: Confirm `git log --oneline` shows the per-task commits**

Run: `git log --oneline df6b24a..HEAD | head -20`

Expected: The Phase 1 commits followed by 7 Phase 2 task commits (Tasks 1-7), in order. No merge commits.

- [ ] **Step 4: Capture the final HEAD SHA**

Run: `git rev-parse HEAD`

Record this for the final review subagent dispatch.

---

## Out of scope

- Replacing argparse entirely.
- Real-Ctrl+C signal handling during `await`.
- An `await runner.invoke_async(...)` test helper.
- Removing pre-existing duplicate definitions of `_DARK_THEMES`/`_LIGHT_THEMES` in `clir/output/style.py` (flagged during Phase 1 reviews; unrelated to Phase 2 scope).
