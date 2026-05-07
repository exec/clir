#!/usr/bin/env python3
"""
taskman — A task manager CLI built with clir.

Demonstrates:
  Core:       ClirApp (name/description/version), @app.command(), @app.group(),
              @argument(), @option(), async command, context object
  Output:     echo, success, error, warning, info, debug
              Table (title/show_lines/box/add_rows/chaining)
              Panel (border_style variations)
              Spinner (context manager)
              Progress (set_total/update + Progress.wrap)
              set_theme / get_theme / get_available_themes / get_terminal_capability
  Prompts:    prompt (with validator), confirm, select, multiselect
  Groups:     @app.group() → @group.command() subcommands

Usage:
    python taskman.py --version
    python taskman.py add "Buy milk" --priority high --tag shopping
    python taskman.py list
    python taskman.py list --include-done
    python taskman.py show 1
    python taskman.py done 1
    python taskman.py interactive
    python taskman.py export --format json
    python taskman.py tag add 1 urgent
    python taskman.py tag list 1
    python taskman.py theme set dracula
    python taskman.py theme list
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from clir import ClirApp, argument, option
from clir.output import (
    Progress,
    Panel,
    Spinner,
    Table,
    echo,
    error,
    get_available_themes,
    get_terminal_capability,
    get_theme,
    info,
    set_theme,
    success,
    warning,
    debug,
)
from clir.prompts import confirm, multiselect, prompt, select

# ── Storage ──────────────────────────────────────────────────────────────────

TASKS_FILE = Path.home() / ".clir_taskman.json"

PRIORITIES = ["low", "medium", "high"]
PRIORITY_STYLE = {
    "low": "dim",
    "medium": "yellow",
    "high": "red bold",
}


def load_tasks() -> list[dict[str, Any]]:
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text())
    return []


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def next_id(tasks: list[dict[str, Any]]) -> int:
    return max((t["id"] for t in tasks), default=0) + 1


def find_task(tasks: list[dict[str, Any]], task_id: int) -> dict[str, Any] | None:
    return next((t for t in tasks if t["id"] == task_id), None)


# ── App ───────────────────────────────────────────────────────────────────────

app = ClirApp(
    name="taskman",
    description="A task manager built with clir",
    version="1.0.0",
)

# ── Commands ──────────────────────────────────────────────────────────────────


@app.command()
@argument("title")
@option("--priority", "-p", default="medium", help="Priority: low, medium, high")
@option("--tag", "-t", help="Tag to attach to the task")
def add(title: str, priority: str, tag: str):
    """Add a new task."""
    if priority not in PRIORITIES:
        error(f"Priority must be one of: {', '.join(PRIORITIES)}")
        return

    tasks = load_tasks()
    task: dict[str, Any] = {
        "id": next_id(tasks),
        "title": title,
        "priority": priority,
        "done": False,
        "tags": [tag] if tag else [],
    }
    tasks.append(task)
    save_tasks(tasks)
    success(f"Added task #{task['id']}: {title}")


@app.command(name="list")
@option("--include-done", "-a", default=False, help="Include completed tasks")
@option("--priority", "-p", help="Filter by priority level")
def list_tasks(include_done: bool, priority: str):
    """List tasks in a formatted table."""
    tasks = load_tasks()

    if not include_done:
        tasks = [t for t in tasks if not t["done"]]
    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]

    if not tasks:
        warning("No tasks found.")
        return

    # Table with title, rounded box, and row lines
    table = Table(
        "ID", "Title", "Priority", "Tags", "Status",
        title="Tasks",
        show_lines=True,
        box="rounded",
    )
    for task in tasks:
        style = PRIORITY_STYLE[task["priority"]]
        status = "[green]✓ done[/green]" if task["done"] else "[yellow]● pending[/yellow]"
        table.add_row(
            str(task["id"]),
            task["title"],
            f"[{style}]{task['priority']}[/{style}]",
            ", ".join(task.get("tags", [])) or "—",
            status,
        )
    table.show()

    pending = sum(1 for t in tasks if not t["done"])
    info(f"{pending} pending, {len(tasks) - pending} done")


@app.command()
@argument("task_id", type=int)
def show(task_id: int, context):
    """Show full task details in a panel (also demonstrates context object)."""
    tasks = load_tasks()
    task = find_task(tasks, task_id)

    if not task:
        error(f"No task with ID {task_id}")
        return

    status = "[green]✓ done[/green]" if task["done"] else "[yellow]● pending[/yellow]"
    border = "green" if task["done"] else "blue"
    style = PRIORITY_STYLE[task["priority"]]

    content = (
        f"[bold]Title:[/bold]    {task['title']}\n"
        f"[bold]Priority:[/bold] [{style}]{task['priority']}[/{style}]\n"
        f"[bold]Tags:[/bold]     {', '.join(task.get('tags', [])) or 'none'}\n"
        f"[bold]Status:[/bold]   {status}"
    )
    # Panel with dynamic border_style
    Panel(content, title=f"Task #{task_id}", border_style=border).show()

    # Context object — carries command name and parsed args
    debug(f"[context] command={context.command_name}  args={context.args}")


@app.command()
@argument("task_id", type=int)
def done(task_id: int):
    """Mark a task as complete."""
    tasks = load_tasks()
    task = find_task(tasks, task_id)

    if not task:
        error(f"No task with ID {task_id}")
        return
    if task["done"]:
        warning(f"Task #{task_id} is already done.")
        return

    # confirm() prompt
    if confirm(f"Mark '{task['title']}' as done?", default=True):
        task["done"] = True
        save_tasks(tasks)
        success(f"Task #{task_id} marked as done!")
    else:
        info("Cancelled.")


@app.command()
@argument("task_id", type=int)
def remove(task_id: int):
    """Remove a task permanently."""
    tasks = load_tasks()
    task = find_task(tasks, task_id)

    if not task:
        error(f"No task with ID {task_id}")
        return

    if confirm(f"Permanently remove '{task['title']}'?", default=False):
        tasks.remove(task)
        save_tasks(tasks)
        success(f"Task #{task_id} removed.")
    else:
        info("Cancelled.")


@app.command()
def clear():
    """Remove all completed tasks."""
    tasks = load_tasks()
    done_tasks = [t for t in tasks if t["done"]]

    if not done_tasks:
        info("No completed tasks to clear.")
        return

    if confirm(f"Clear {len(done_tasks)} completed task(s)?", default=False):
        save_tasks([t for t in tasks if not t["done"]])
        success(f"Cleared {len(done_tasks)} task(s).")
    else:
        info("Cancelled.")


@app.command()
def interactive():
    """Interactively create a task using prompts."""
    echo("\n[bold]Create a new task[/bold]\n")

    # prompt() with a validator — re-prompts until non-empty input is given
    title = prompt(
        "Task title",
        validator=lambda v: v.strip() if v.strip() else None,
    )

    # select() — numbered list, default highlights "medium"
    priority = select(
        PRIORITIES,
        message="Priority",
        default=1,
    )

    # multiselect() — pick zero or more tags
    available_tags = ["work", "personal", "urgent", "shopping", "health", "learning"]
    tags = multiselect(available_tags, message="Tags (optional, press Enter to skip)")

    # confirm() — final check before saving
    if confirm(f"\nAdd task '{title}' [{priority}]?", default=True):
        tasks = load_tasks()
        task: dict[str, Any] = {
            "id": next_id(tasks),
            "title": title,
            "priority": priority,
            "done": False,
            "tags": tags,
        }
        tasks.append(task)
        save_tasks(tasks)
        success(f"Added task #{task['id']}: {title}")
    else:
        info("Cancelled.")


@app.command()
@option("--format", "-f", default="table", help="Output format: table or json")
async def export(format: str):
    """Export all tasks — async command with Spinner and Progress."""
    tasks = load_tasks()
    if not tasks:
        warning("No tasks to export.")
        return

    # Spinner as context manager — animates while awaiting
    with Spinner("Preparing export..."):
        await asyncio.sleep(0.4)

    if format == "json":
        echo(json.dumps(tasks, indent=2))
    else:
        # Progress (manual total + update) — shows bar and time remaining
        with Progress("Exporting tasks") as progress:
            progress.set_total(len(tasks))
            rows = []
            for task in tasks:
                rows.append([
                    str(task["id"]),
                    task["title"],
                    task["priority"],
                    "yes" if task["done"] else "no",
                    ", ".join(task.get("tags", [])) or "—",
                ])
                progress.update(1)

        # Table chaining — add_rows returns self
        Table("ID", "Title", "Priority", "Done", "Tags", title="Export") \
            .add_rows(rows) \
            .show()

    success(f"Exported {len(tasks)} task(s).")


# ── Tag Group ─────────────────────────────────────────────────────────────────


@app.group()
def tag():
    """Manage task tags."""


@tag.command(name="add")
@argument("task_id", type=int)
@argument("name")
def tag_add(task_id: int, name: str):
    """Add a tag to a task."""
    tasks = load_tasks()
    task = find_task(tasks, task_id)
    if not task:
        error(f"No task with ID {task_id}")
        return
    if name in task.get("tags", []):
        warning(f"Tag '{name}' already on task #{task_id}.")
        return
    task.setdefault("tags", []).append(name)
    save_tasks(tasks)
    success(f"Tagged task #{task_id} with '{name}'")


@tag.command(name="remove")
@argument("task_id", type=int)
@argument("name")
def tag_remove(task_id: int, name: str):
    """Remove a tag from a task."""
    tasks = load_tasks()
    task = find_task(tasks, task_id)
    if not task:
        error(f"No task with ID {task_id}")
        return
    if name not in task.get("tags", []):
        warning(f"Tag '{name}' not on task #{task_id}.")
        return
    task["tags"].remove(name)
    save_tasks(tasks)
    success(f"Removed tag '{name}' from task #{task_id}")


@tag.command(name="list")
@argument("task_id", type=int)
def tag_list(task_id: int):
    """List tags on a task."""
    tasks = load_tasks()
    task = find_task(tasks, task_id)
    if not task:
        error(f"No task with ID {task_id}")
        return

    tags = task.get("tags", [])
    if not tags:
        info(f"Task #{task_id} has no tags.")
        return

    # Simple table with a title, no box lines
    table = Table("Tag", title=f"Tags for task #{task_id}")
    for t in tags:
        table.add_row(t)
    table.show()


# ── Theme Group ───────────────────────────────────────────────────────────────


@app.group()
def theme():
    """Manage the output theme."""


@theme.command(name="set")
@argument("name")
def theme_set(name: str):
    """Apply an output theme for this session."""
    try:
        set_theme(name)
        success(f"Theme set to '{name}'")
        info("Sample info message")
        warning("Sample warning message")
        error("Sample error message (styled, not a real error)")
    except ValueError:
        available = get_available_themes()
        error(f"Unknown theme '{name}'.")
        info(f"Available: {', '.join(available)}")


@theme.command(name="list")
def theme_list():
    """List available themes and terminal capability."""
    capability = get_terminal_capability()
    current = get_theme()

    info(f"Terminal colour capability: [bold]{capability}[/bold]")
    echo()

    # Table with simple box style
    table = Table("Theme", "Active", title="Available Themes", box="simple")
    for th in get_available_themes():
        table.add_row(th, "✓" if th == current else "")
    table.show()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run()
