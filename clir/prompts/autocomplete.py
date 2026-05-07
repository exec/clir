"""Auto-complete support for prompts."""

from typing import Callable

from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.document import Document


class DynamicCompleter(Completer):
    """A completer that uses a callback to get completion choices.

    Args:
        get_choices: A callable that returns a list of choices based on current input
        case_sensitive: Whether prefix matching is case-sensitive
    """

    def __init__(self, get_choices: Callable[[str], list[str]], case_sensitive: bool = True):
        self.get_choices = get_choices
        self.case_sensitive = case_sensitive

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        choices = self.get_choices(text)
        for word in choices:
            cmp_word = word if self.case_sensitive else word.lower()
            cmp_text = text if self.case_sensitive else text.lower()
            if cmp_word.startswith(cmp_text):
                yield Completion(word, start_position=-len(text))


def autocomplete(
    choices: list[str] | Callable[[str], list[str]],
    case_sensitive: bool = True,
) -> Completer:
    """Create an auto-completer for prompts.

    Args:
        choices: List of choices or a callable that returns choices based on input
        case_sensitive: Whether matching is case-sensitive

    Returns:
        A Completer instance

    Examples:
        >>> from clir.prompts import prompt
        >>> completer = autocomplete(["apple", "banana", "cherry"])
        >>> prompt("Choose fruit", completer=completer)
    """
    if callable(choices):
        return DynamicCompleter(choices, case_sensitive=case_sensitive)
    return WordCompleter(choices, case_sensitive=case_sensitive)


def subcommand_completer(commands: dict, groups: dict | None = None) -> Completer:
    """Create a completer for subcommands.

    Args:
        commands: Dict of command name -> Command
        groups: Dict of group name -> Group (for nested completion)

    Returns:
        A Completer instance for subcommands
    """
    choices = list(commands.keys())
    if groups:
        choices.extend(groups.keys())
    return WordCompleter(choices, case_sensitive=False)


def nested_completer(
    get_choices: Callable[[list[str]], list[str]],
) -> Completer:
    """Create a completer for nested subcommands.

    Args:
        get_choices: Function that takes current command path and returns choices

    Returns:
        A Completer for nested commands
    """
    return DynamicCompleter(get_choices)
