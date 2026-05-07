"""Group infrastructure for CLI commands."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from clir.core.command import Command
from clir.core.context import Context

F = TypeVar("F", bound=Callable[..., Any])


class Group(Command):
    """A group of subcommands (like `git` with `git commit`, `git push`)."""

    def __init__(
        self,
        func: Callable[..., Any],
        name: str | None = None,
        help: str | None = None,
    ):
        super().__init__(func, name=name, help=help)
        self.commands: dict[str, Command | Group] = {}
        self._default_command: Command | None = None

    def register(self, cmd: Command | Group) -> None:
        """Register a subcommand with this group."""
        self.commands[cmd.name] = cmd

    def command(
        self,
        name: str | None = None,
        help: str | None = None,
    ) -> Callable[[Callable[..., Any]], Command | Group]:
        """Decorator to add a subcommand to this group."""

        def decorator(func: Callable[..., Any]) -> Command | Group:
            # Check if function already has a command (from @argument/@option decorators)
            existing_cmd: Command | None = getattr(func, "_clir_command", None)
            if existing_cmd:
                # Reuse existing command, just update name/help and register
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
        """Decorator to add a sub-group to this group."""

        def decorator(func: Callable[..., Any]) -> Group:
            group = Group(func, name=name, help=help)
            self.register(group)
            return group

        return decorator

    def default(self, cmd: Command | None = None) -> Command | None:
        """Set or get the default subcommand."""
        if cmd is not None:
            self._default_command = cmd
            return cmd
        return self._default_command

    async def run(self, args: dict[str, Any], parent: Context | None = None) -> Any:
        """Run the group with parsed arguments."""
        # Get subcommand from args - support both "command" and "subcommand" keys
        subcommand_name = args.get("subcommand") or args.get("command")
        cmd_args = {k: v for k, v in args.items() if k not in ("command", "subcommand")}

        if not subcommand_name:
            # No subcommand specified
            if self._default_command:
                ctx = Context(self.name, cmd_args, parent)
                return await self._default_command.run(cmd_args, ctx)
            else:
                # Print help for this group
                print(f"Usage: {self.name} <command>")
                print()
                print("Available commands:")
                for name, cmd in self.commands.items():
                    print(f"  {name:15} {cmd.help or ''}")
                return

        # Find the subcommand
        subcmd = self.commands.get(subcommand_name)
        if not subcmd:
            raise ValueError(f"Unknown command '{subcommand_name}'. Run '{self.name} --help' for available commands.")

        ctx = Context(self.name, cmd_args, parent)
        return await subcmd.run(cmd_args, ctx)

    def __repr__(self) -> str:
        return f"Group({self.name})"


def group(name: str | None = None, help: str | None = None) -> Callable[[F], Group]:
    """Decorator to register a function as a CLI group."""

    def decorator(func: F) -> Group:
        grp = Group(func, name=name, help=help)
        # Attach group to function for later retrieval
        func._clir_group = grp  # type: ignore
        return grp  # type: ignore

    return decorator
