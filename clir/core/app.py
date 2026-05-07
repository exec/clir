"""Main ClirApp application class."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Callable

from clir.core.command import Command
from clir.core.context import Context
from clir.core.group import Group
from clir.aliases import AliasManager
from clir.hooks import Hooks


class ClirApp:
    """Main CLI application class."""

    def __init__(
        self,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.name = name or "cli"
        self.description = description
        self.version = version
        self.commands: dict[str, Command | Group] = {}
        self._default_command: Command | None = None
        self._config: dict[str, Any] = config or {}
        self._alias_manager: AliasManager | None = None
        self._hooks: Hooks | None = None
        self._quiet: bool = False
        self._verbose: bool = False
        self._debug: bool = False
        self._json_mode: bool = False
        self._pretty: bool = False
        self._search: str | None = None

    @property
    def quiet(self) -> bool:
        """Check if quiet mode is enabled."""
        return self._quiet

    @property
    def verbose(self) -> bool:
        """Check if verbose mode is enabled."""
        return self._verbose

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._debug

    @property
    def json_mode(self) -> bool:
        """Check if JSON output mode is enabled."""
        return self._json_mode

    @property
    def pretty(self) -> bool:
        """Check if pretty print mode is enabled."""
        return self._pretty

    def set_quiet(self, value: bool = True) -> None:
        """Set quiet mode."""
        self._quiet = value

    def set_verbose(self, value: bool = True) -> None:
        """Set verbose mode."""
        self._verbose = value

    def set_debug(self, value: bool = True) -> None:
        """Set debug mode."""
        self._debug = value

    # Global flags that only work at the start (before command)
    _GLOBAL_FLAGS_START = {"--quiet", "-q", "--verbose", "-v", "--debug", "-d"}
    # Global flags that can appear anywhere (output format flags)
    _GLOBAL_FLAGS_ANYWHERE = {"--json", "-j", "--pretty", "-p"}
    # All global flags
    _GLOBAL_FLAGS = _GLOBAL_FLAGS_START | _GLOBAL_FLAGS_ANYWHERE

    def _parse_global_flags(self, argv: list[str]) -> list[str]:
        """Parse global flags from argv (before command).

        Args:
            argv: Command-line arguments

        Returns:
            argv with global flags removed
        """
        # Find where command starts (first non-flag arg or --)
        command_start = 0
        for i, arg in enumerate(argv):
            if arg == "--":
                command_start = i + 1
                break
            # Stop at first positional argument (not starting with -)
            if not arg.startswith("-"):
                command_start = i
                break

        # Parse global flags only from the part before command
        pre_command = argv[:command_start]
        post_command = argv[command_start:]

        new_argv = []
        skip_next = False
        for i, arg in enumerate(pre_command):
            if skip_next:
                skip_next = False
                continue

            # Check if this is a global flag
            if arg in self._GLOBAL_FLAGS:
                if arg == "--quiet" or arg == "-q":
                    self._quiet = True
                elif arg == "--verbose" or arg == "-v":
                    self._verbose = True
                elif arg == "--debug" or arg == "-d":
                    self._debug = True
                    self._verbose = True
                elif arg == "--json" or arg == "-j":
                    self._json_mode = True
                elif arg == "--pretty" or arg == "-p":
                    self._pretty = True
                # Skip adding to new_argv (consume the flag)
            elif arg.startswith("--search="):
                self._search = arg.split("=", 1)[1]
            elif arg == "--search" and i + 1 < len(pre_command):
                self._search = pre_command[i + 1]
                skip_next = True
            elif arg.startswith("--debug="):
                # Let argparse handle it
                new_argv.append(arg)
            else:
                new_argv.append(arg)

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

    @property
    def hooks(self) -> Hooks:
        """Get the hooks manager, creating if needed."""
        if self._hooks is None:
            self._hooks = Hooks()
        return self._hooks

    @property
    def aliases(self) -> AliasManager:
        """Get the alias manager, creating if needed."""
        if self._alias_manager is None:
            self._alias_manager = AliasManager()
        return self._alias_manager
        self._aliases: dict[str, str] = {}  # alias -> command mapping

    def register(self, cmd: Command | Group) -> None:
        """Register a command or group with the app."""
        self.commands[cmd.name] = cmd

    def command(
        self,
        name: str | None = None,
        help: str | None = None,
    ) -> Callable[[Callable[..., Any]], Command]:
        """Decorator to register a command."""

        def decorator(func: Callable[..., Any]) -> Command:
            # Check if function already has a command (from @argument/@option decorators)
            existing_cmd: Command | None = getattr(func, "_clir_command", None)
            if existing_cmd:
                # Reuse existing command, just update name/help
                if name:
                    existing_cmd.name = name
                if help:
                    existing_cmd.help = help
                self.register(existing_cmd)
                return existing_cmd
            else:
                cmd = Command(func, name=name, help=help)
                self.register(cmd)
                return cmd

        return decorator

    def group(
        self,
        name: str | None = None,
        help: str | None = None,
    ) -> Callable[[Callable[..., Any]], Group]:
        """Decorator to register a command group (for subcommands)."""

        def decorator(func: Callable[..., Any]) -> Group:
            # Check if function already has a group
            existing_group: Group | None = getattr(func, "_clir_group", None)
            if existing_group:
                if name:
                    existing_group.name = name
                if help:
                    existing_group.help = help
                self.register(existing_group)
                return existing_group
            else:
                group = Group(func, name=name, help=help)
                self.register(group)
                return group

        return decorator

    def default(self, cmd: Command | None = None) -> Command | None:
        """Set or get the default command."""
        if cmd is not None:
            self._default_command = cmd
            return cmd
        return self._default_command

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

    def _run_group_command(self, group: Group, argv: list[str]) -> None:
        """Recursively run a group command, handling nested groups.

        Args:
            group: The group to run
            argv: Remaining command-line arguments after the group name
        """
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
            )
            self._populate_subparsers(group_parser, group.commands)

            parsed = vars(group_parser.parse_args(argv))
            try:
                asyncio.run(group.run(parsed, parent=None))
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

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

    def _add_command_params(
        self,
        parser: argparse.ArgumentParser,
        cmd: Command,
        reverse_args: bool = False,
    ) -> None:
        """Add arguments and options to an argparse parser.

        Args:
            parser: The argparse parser to add arguments to
            cmd: The command to extract params from
            reverse_args: If True, reverse argument order (for subcommands where decorators are applied bottom-up)
        """
        params = cmd.params
        args_params = [p for p in params if p.param_type.value == "argument"]
        opts_params = [p for p in params if p.param_type.value == "option"]

        # Add arguments (potentially reversed)
        for param in (reversed(args_params) if reverse_args else args_params):
            parser.add_argument(
                param.name,
                type=param.type,
                default=param.default,
                help=param.help,
            )

        # Add options
        for param in opts_params:
            args = []
            if param.short:
                short = param.short.lstrip("-")
                args.append(f"-{short}")
            args.append(f"--{param.name.replace('_', '-')}")
            if param.type is bool:
                if param.default:
                    parser.add_argument(
                        *args, action="store_false", help=param.help
                    )
                else:
                    parser.add_argument(
                        *args, action="store_true", help=param.help
                    )
            else:
                parser.add_argument(
                    *args,
                    type=param.type,
                    default=param.default,
                    help=param.help,
                )

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

    def _parse_args(self, argv: list[str]) -> dict[str, Any]:
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
        )
        self._populate_subparsers(parser, self.commands, dest="command")
        return vars(parser.parse_args(argv))

    def _suggest_command(self, name: str) -> str | None:
        """Suggest a command name using fuzzy matching.

        Args:
            name: The command name that wasn't found

        Returns:
            Suggested command name or None
        """
        if not name or len(name) < 2:
            return None

        # Simple Levenshtein-like distance
        def distance(a: str, b: str) -> int:
            """Calculate edit distance between two strings."""
            if len(a) > len(b):
                a, b = b, a
            distances = list(range(len(a) + 1))
            for i, char_b in enumerate(b, 1):
                new_distances = [i]
                for j, char_a in enumerate(a, 1):
                    if char_a == char_b:
                        new_distances.append(distances[j])
                    else:
                        new_distances.append(1 + min(distances[j], distances[j - 1], new_distances[-1]))
                distances = new_distances
            return distances[-1]

        # Check for prefix match (input starts with command, like "he" -> "hello")
        for cmd_name in self.commands:
            if name.startswith(cmd_name) or cmd_name.startswith(name):
                return cmd_name

        # Check for substring match (command contains input)
        for cmd_name in self.commands:
            if name in cmd_name:
                return cmd_name

        # Find closest match
        best_match = None
        best_distance = float('inf')

        for cmd_name in self.commands:
            # Skip groups for direct command suggestions
            if isinstance(self.commands[cmd_name], Group):
                continue
            dist = distance(name.lower(), cmd_name.lower())
            # Use threshold of half the command name length (with max of 5)
            threshold = max(5, len(name) // 2 + 1)
            if dist <= threshold and dist < best_distance:
                best_distance = dist
                best_match = cmd_name

        return best_match

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

    def generate_completion(self, shell: str) -> str:
        """Generate shell completion script.

        Args:
            shell: Shell type ('bash', 'zsh', or 'fish')

        Returns:
            Shell completion script

        Raises:
            ValueError: If shell type is not supported
        """
        from clir.completion import generate_completion

        return generate_completion(shell, self.commands, self.name)

    def print_completion(self, shell: str) -> None:
        """Print completion script to stdout.

        Args:
            shell: Shell type ('bash', 'zsh', or 'fish')
        """
        print(self.generate_completion(shell))

    @property
    def config(self) -> dict[str, Any]:
        """Get the current configuration."""
        return self._config

    def load_config(self, path: str | None = None) -> dict[str, Any]:
        """Load configuration from file.

        Args:
            path: Config file path (YAML, JSON, or TOML).
                  If None, auto-discovers config file.

        Returns:
            Loaded configuration dictionary
        """
        from clir.config import get_config

        config = get_config(name=self.name, path=path)
        self._config = config
        return config

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a config value with optional default.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)


def main() -> None:
    """Entry point for the CLI."""
    app = ClirApp()
    app.run()
