#!/usr/bin/env python3
"""
devtools — A developer utilities CLI built with clir.

Demonstrates:
  Core:       Nested groups (@group.group() → @subgroup.command())
              Standalone @group decorator (top-level group object)
  Output:     Spinner (manual start/stop/update API)
              Progress (set_total + update)
              Progress.wrap() for iterables
              Panel with several border_style values
              Table with box / style / show_lines / min_width options
  Prompts:    password(), confirm_password()
              autocomplete() — WordCompleter and DynamicCompleter
              prompt_input() with completer kwarg
  Security:   validate_path(), is_safe_path() from clir.utils

Usage:
    python devtools.py --version
    python devtools.py info
    python devtools.py scan /tmp
    python devtools.py scan /tmp --recursive --base /tmp
    python devtools.py check /etc/passwd --base /tmp
    python devtools.py config list
    python devtools.py config set editor nano
    python devtools.py config interactive
    python devtools.py config reset
    python devtools.py auth login
    python devtools.py auth whoami
    python devtools.py auth passwd
    python devtools.py auth logout
    python devtools.py auth token create --name mytoken
    python devtools.py auth token revoke mytoken
    python devtools.py init
"""

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

from clir import ClirApp, argument, group, option
from clir.output import (
    Panel,
    Progress,
    Spinner,
    Table,
    echo,
    error,
    get_terminal_capability,
    info,
    success,
    warning,
)
from clir.prompts import autocomplete, confirm, confirm_password, multiselect, password, prompt, select
from clir.utils import is_safe_path, validate_path

# ── Storage ───────────────────────────────────────────────────────────────────

CONFIG_FILE = Path.home() / ".clir_devtools.json"
SESSION_FILE = Path.home() / ".clir_devtools_session.json"

KNOWN_CONFIG_KEYS = [
    "editor", "theme", "log_level", "output_format",
    "base_path", "timeout", "max_results", "debug_mode",
]

DEFAULT_CONFIG: dict[str, str] = {
    "editor": "vim",
    "theme": "default",
    "log_level": "info",
    "output_format": "table",
    "base_path": str(Path.home()),
    "timeout": "30",
    "max_results": "100",
    "debug_mode": "false",
}


def load_config() -> dict[str, str]:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict[str, str]) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def load_session() -> dict[str, Any] | None:
    if SESSION_FILE.exists():
        return json.loads(SESSION_FILE.read_text())
    return None


def save_session(session: dict[str, Any]) -> None:
    SESSION_FILE.write_text(json.dumps(session, indent=2))


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


# ── App ───────────────────────────────────────────────────────────────────────

app = ClirApp(
    name="devtools",
    description="Developer utilities built with clir",
    version="2.0.0",
)

# ── Top-level commands ────────────────────────────────────────────────────────


@app.command(name="info")
def sys_info():
    """Show terminal and environment info using Spinner (manual API)."""
    # Spinner manual start/stop/update — no context manager needed
    spinner = Spinner("Gathering system info...")
    spinner.start()

    import platform
    data = {
        "Platform": platform.system(),
        "Python": platform.python_version(),
        "Terminal": os.environ.get("TERM", "unknown"),
        "Colour support": get_terminal_capability(),
        "Shell": os.environ.get("SHELL", "unknown"),
    }
    try:
        data["Columns"] = str(os.get_terminal_size().columns)
    except OSError:
        data["Columns"] = "N/A"

    spinner.update("Rendering...")
    spinner.stop()

    content = "\n".join(f"[bold]{k}:[/bold] {v}" for k, v in data.items())
    # Panel with cyan border
    Panel(content, title="System Info", border_style="cyan").show()


@app.command()
@argument("path")
@option("--recursive", "-r", default=False, help="Scan recursively")
@option("--base", "-b", help="Restrict to this base directory (path safety check)")
def scan(path: str, recursive: bool, base: str):
    """Scan a directory, validating paths and listing files with Progress.wrap."""
    # validate_path raises ValueError on traversal; returns resolved Path
    try:
        resolved = validate_path(path, base_dir=base if base else None)
    except ValueError as e:
        error(str(e))
        return

    if not resolved.exists():
        error(f"Path does not exist: {resolved}")
        return
    if not resolved.is_dir():
        error(f"Not a directory: {resolved}")
        return

    info(f"Scanning [bold]{resolved}[/bold]{'  (recursive)' if recursive else ''}")

    pattern = "**/*" if recursive else "*"
    files = [p for p in resolved.glob(pattern) if p.is_file()]

    if not files:
        warning("No files found.")
        return

    # Progress.wrap() — wraps any iterable with a progress bar
    rows: list[list[str]] = []
    for f in Progress.wrap(files, description="Scanning..."):
        safe = is_safe_path(str(f), base_dir=str(resolved))
        size = f"{f.stat().st_size / 1024:.1f} KB"
        rows.append([f.name, f.suffix or "—", size, "✓" if safe else "✗"])

    # Table with simple box style and a colour style applied
    Table(
        "Name", "Type", "Size", "Safe",
        title=f"Files in {resolved.name}/",
        box="simple",
        style="cyan",
        show_lines=False,
        min_width=60,
    ).add_rows(rows).show()

    success(f"Found {len(files)} file(s).")


@app.command()
@argument("path")
@option("--base", "-b", help="Base directory to check against")
def check(path: str, base: str):
    """Check whether a path is safe (no directory traversal). Demonstrates is_safe_path."""
    safe = is_safe_path(path, base_dir=base if base else None)
    resolved = Path(path).resolve()

    if safe:
        Panel(
            f"[bold]Input:[/bold]    {path}\n"
            f"[bold]Resolved:[/bold] {resolved}\n"
            f"[bold]Status:[/bold]   [green]Safe ✓[/green]",
            title="Path Check",
            border_style="green",
        ).show()
    else:
        Panel(
            f"[bold]Input:[/bold]    {path}\n"
            f"[bold]Resolved:[/bold] {resolved}\n"
            f"[bold]Status:[/bold]   [red]Unsafe — possible traversal ✗[/red]",
            title="Path Check",
            border_style="red",
        ).show()


@app.command()
@option("--name", "-n", help="Project name (skips prompt if provided)")
def init(name: str):
    """Initialize a new project — demonstrates select and multiselect."""
    echo("\n[bold]New Project Setup[/bold]\n")

    if not name:
        name = prompt("Project name", validator=lambda v: v.strip() if v.strip() else None)

    # select() — single choice with a pre-selected default (index 1)
    template = select(
        ["python-library", "cli-tool", "web-api", "data-pipeline"],
        message="Template",
        default=1,
    )

    # multiselect() — multiple choices; some pre-selected via default indices
    features = multiselect(
        ["tests", "ci/cd", "docker", "linting", "docs", "pre-commit hooks"],
        message="Features to include",
        default=[0, 1, 3],  # tests, ci/cd, linting pre-ticked
    )

    if not confirm(f"\nCreate '{name}' with template '{template}'?", default=True):
        info("Cancelled.")
        return

    # Progress (manual) — shows bar while doing setup steps
    steps = ["Creating structure", "Writing config", "Installing hooks"] + features
    with Progress(f"Initialising {name}") as progress:
        progress.set_total(len(steps))
        for step in steps:
            time.sleep(0.08)
            progress.update(1, description=step)

    # Table with double-edge box for a polished summary
    table = Table("Item", "Status", title=f"Project: {name}", box="square_double_head")
    table.add_row(f"Template: {template}", "[green]✓[/green]")
    for feat in features:
        table.add_row(f"  + {feat}", "[green]✓[/green]")
    table.show()

    success(f"Project '{name}' ready!")


# ── Config group ──────────────────────────────────────────────────────────────


@app.group()
def config():
    """Manage tool configuration."""


@config.command(name="set")
@argument("key")
@argument("value")
def config_set(key: str, value: str):
    """Set a configuration value."""
    cfg = load_config()
    if key not in KNOWN_CONFIG_KEYS:
        warning(f"'{key}' is not a recognised key.")
        if not confirm("Set it anyway?", default=False):
            return
    cfg[key] = value
    save_config(cfg)
    success(f"Set [bold]{key}[/bold] = {value}")


@config.command(name="get")
@argument("key")
def config_get(key: str):
    """Get a configuration value."""
    cfg = load_config()
    if key not in cfg:
        error(f"Key '{key}' is not set.")
        return
    echo(f"{key} = [bold]{cfg[key]}[/bold]")


@config.command(name="list")
def config_list():
    """List all configuration values."""
    cfg = load_config()

    # Table with double box, row lines, and a width minimum
    table = Table(
        "Key", "Value", "Default?",
        title="Configuration",
        box="double",
        show_lines=True,
        min_width=55,
    )
    for key, value in cfg.items():
        is_default = value == DEFAULT_CONFIG.get(key)
        default_marker = "[dim]yes[/dim]" if is_default else "[yellow]modified[/yellow]"
        table.add_row(key, value, default_marker)
    table.show()


@config.command(name="interactive")
def config_interactive():
    """Set a config value using autocomplete prompts."""
    cfg = load_config()

    # autocomplete() with a static list → WordCompleter
    key_completer = autocomplete(KNOWN_CONFIG_KEYS, case_sensitive=False)

    key = prompt("Config key (Tab to complete)", completer=key_completer)

    if not key.strip():
        warning("No key entered.")
        return

    # autocomplete() with a callable → DynamicCompleter
    def suggest_values(text: str) -> list[str]:
        suggestions: dict[str, list[str]] = {
            "log_level": ["debug", "info", "warning", "error"],
            "output_format": ["table", "json", "csv"],
            "debug_mode": ["true", "false"],
            "theme": ["default", "dracula", "monokai", "nord"],
        }
        return [v for v in suggestions.get(key, []) if v.startswith(text)]

    value_completer = autocomplete(suggest_values)
    current = cfg.get(key, "")
    value = prompt(f"Value for '{key}'", default=current, completer=value_completer)

    cfg[key] = value
    save_config(cfg)
    success(f"Set [bold]{key}[/bold] = {value}")


@config.command(name="reset")
def config_reset():
    """Reset all configuration to defaults."""
    if confirm("Reset all config to defaults?", default=False):
        save_config(DEFAULT_CONFIG.copy())
        success("Configuration reset to defaults.")
    else:
        info("Cancelled.")


# ── Auth group ────────────────────────────────────────────────────────────────


@app.group()
def auth():
    """Authentication and session management."""


@auth.command()
@option("--username", "-u", help="Username (skips prompt if provided)")
def login(username: str):
    """Log in. Demonstrates the password() prompt."""
    session = load_session()
    if session:
        warning(f"Already logged in as [bold]{session['username']}[/bold]. Log out first.")
        return

    if not username:
        username = prompt("Username", validator=lambda v: v.strip() if v.strip() else None)

    # password() — masked input
    pwd = password("Password")
    if not pwd:
        error("Password cannot be empty.")
        return

    with Spinner(f"Logging in as {username}..."):
        time.sleep(0.4)  # simulate network auth

    save_session({"username": username})
    success(f"Logged in as [bold]{username}[/bold]")


@auth.command()
def logout():
    """Log out of the current session."""
    session = load_session()
    if not session:
        warning("Not logged in.")
        return

    if confirm(f"Log out as {session['username']}?", default=True):
        clear_session()
        success("Logged out.")
    else:
        info("Cancelled.")


@auth.command()
def whoami():
    """Show the current logged-in user."""
    session = load_session()
    if not session:
        Panel(
            "[yellow]Not logged in.[/yellow]\nRun [bold]devtools auth login[/bold] first.",
            title="Session",
            border_style="yellow",
        ).show()
        return

    Panel(
        f"[bold]Username:[/bold] {session['username']}",
        title="Current Session",
        border_style="green",
    ).show()


@auth.command()
def passwd():
    """Change password — demonstrates confirm_password()."""
    session = load_session()
    if not session:
        error("Not logged in.")
        return

    # confirm_password() — prompts twice, enforces minimum length, re-prompts on mismatch
    new_pwd = confirm_password(
        message="New password",
        confirm_message="Confirm new password",
        min_length=8,
    )

    with Spinner("Updating password..."):
        time.sleep(0.3)

    success(f"Password updated. ({len(new_pwd)} characters)")


# ── Auth → Token sub-group (nested group) ─────────────────────────────────────


@auth.group()
def token():
    """Manage authentication tokens (nested group demo)."""


@token.command(name="create")
@option("--name", "-n", default="default", help="Token name")
@option("--expires", "-e", default="30d", help="Expiry period (e.g. 7d, 24h)")
def token_create(name: str, expires: str):
    """Generate a new auth token."""
    session = load_session()
    if not session:
        error("Not logged in.")
        return

    with Spinner(f"Creating token '{name}'..."):
        time.sleep(0.3)
        token_value = secrets.token_hex(24)

    # Panel with green border for success output
    Panel(
        f"[bold]Name:[/bold]    {name}\n"
        f"[bold]Token:[/bold]   [green]{token_value}[/green]\n"
        f"[bold]Expires:[/bold] in {expires}\n\n"
        "[dim]Store this somewhere safe — it won't be shown again.[/dim]",
        title="New Token",
        border_style="green",
    ).show()


@token.command(name="revoke")
@argument("name")
def token_revoke(name: str):
    """Revoke an authentication token."""
    if confirm(f"Revoke token '{name}'?", default=False):
        success(f"Token '{name}' revoked.")
    else:
        info("Cancelled.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run()
