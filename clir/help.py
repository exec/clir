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
