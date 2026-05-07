"""Subcommand completion utilities."""

from typing import Callable
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.document import Document


class CommandCompleter(Completer):
    """Completer for CLI commands and subcommands.

    Args:
        get_commands: Callable that returns list of available commands
        get_options: Optional callable that returns options for a given command
    """

    def __init__(
        self,
        get_commands: Callable[[], list[str]],
        get_options: Callable[[str], list[str]] | None = None,
    ):
        self.get_commands = get_commands
        self.get_options = get_options or (lambda cmd: [])

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        # Split by space to understand context
        parts = text.split()

        if not parts:
            # No input - suggest commands
            commands = self.get_commands()
            for cmd in commands:
                yield Completion(cmd, start_position=0)
        elif len(parts) == 1:
            # Completing first word - suggest commands
            prefix = parts[0]
            commands = self.get_commands()
            for cmd in commands:
                if cmd.startswith(prefix):
                    yield Completion(cmd, start_position=-len(prefix))
        else:
            # Completing options for a command
            cmd = parts[0]
            prefix = parts[-1]
            options = self.get_options(cmd)

            # Add common options
            all_options = options + ["--help", "--version", "--verbose", "--debug", "--quiet"]

            for opt in all_options:
                if opt.startswith(prefix):
                    yield Completion(opt, start_position=-len(prefix))


def complete_commands(commands: dict, prefix: str = "") -> list[str]:
    """Get command names from commands dict.

    Args:
        commands: Dict of command name -> Command/Group
        prefix: Filter prefix

    Returns:
        List of command names
    """
    results = []
    for name, cmd in commands.items():
        if isinstance(cmd, dict):
            # Recursive for nested groups
            results.extend(complete_commands(cmd, prefix))
        elif not prefix or name.startswith(prefix):
            results.append(name)
    return results


__all__ = ["CommandCompleter", "complete_commands"]