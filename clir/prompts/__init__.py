"""Interactive prompts for CLI applications."""

from clir.prompts.input import prompt, password, confirm, confirm_password
from clir.prompts.select import select, multiselect
from clir.prompts.autocomplete import autocomplete

__all__ = [
    "prompt",
    "password",
    "confirm",
    "confirm_password",
    "select",
    "multiselect",
    "autocomplete",
]
