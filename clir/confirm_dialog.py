"""Interactive confirmation dialogs."""

from typing import Any
from clir.prompts.select import select
from clir.prompts.input import confirm


def confirm_action(
    message: str,
    default: bool = False,
) -> bool:
    """Confirm an action with yes/no prompt.

    Args:
        message: Confirmation message
        default: Default value

    Returns:
        True if confirmed, False otherwise
    """
    return confirm(message, default=default)


def confirm_choice(
    message: str,
    choices: list[str],
    default: int | None = None,
) -> str | None:
    """Show a choice confirmation dialog.

    Args:
        message: Message to display
        choices: Available choices
        default: Default choice index

    Returns:
        Selected choice or None
    """
    return select(
        choices=choices,
        message=message,
        default=default,
        autocomplete=False,
    )


def confirm_destructive(
    message: str,
    default: bool = False,
    type_name: str = "action",
) -> bool:
    """Confirm a destructive action with warning.

    Args:
        message: Action description
        default: Default (False for destructive)
        type_name: Type of action (e.g., "delete", "remove")

    Returns:
        True if confirmed
    """
    warning = f"[DESTRUCTIVE] This will {message}. Are you sure?"
    return confirm(warning, default=default)


__all__ = [
    "confirm_action",
    "confirm_choice",
    "confirm_destructive",
]