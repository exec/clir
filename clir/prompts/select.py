"""Selection prompts using prompt_toolkit."""

import sys
from typing import Callable, TypeVar

import prompt_toolkit
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator, ValidationError, Document

T = TypeVar("T")

# Prompt messages
_DEFAULT_SELECT_MESSAGE = "Select an option:"
_DEFAULT_MULTISELECT_MESSAGE = "Select options:"
_ENTER_CHOICE_PROMPT = "Enter choice"
_ENTER_CHOICES_PROMPT = "Enter choices"
_INVALID_CHOICE_MSG = "Invalid choice: "
_INVALID_FORMAT_MSG = "Invalid format, use: 1,2,3"

# Message templates
_VALID_RANGE_MSG = "Please enter a number between 1 and {max}"
_INVALID_NUMBER_MSG = "Please enter a valid number"
_MULTISELECT_FORMAT_HINT = "(Enter numbers separated by commas, e.g., 1,3,5)"
_MULTISELECT_CONFIRM_HINT = "(Press Enter to confirm)"


class _SelectionValidator(Validator):
    """Validator for selection prompts."""

    def __init__(self, choices: list[str]):
        self.choices = choices

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if not text:
            return  # Allow empty (will use default)
        try:
            idx = int(text) - 1
            if not (0 <= idx < len(self.choices)):
                raise ValidationError(
                    message=_VALID_RANGE_MSG.format(max=len(self.choices)),
                    cursor_position=len(text),
                )
        except ValueError:
            raise ValidationError(
                message=_INVALID_NUMBER_MSG,
                cursor_position=len(text),
            )


def select(
    choices: list[str],
    message: str = _DEFAULT_SELECT_MESSAGE,
    default: int | None = None,
    validator: Callable[[str], T | None] | None = None,
    autocomplete: bool = True,
) -> T | str:
    """
    Prompt user to select from a list of choices.

    Args:
        choices: List of choices
        message: The prompt message
        default: Default index (0-based)
        validator: Optional validator
        autocomplete: Enable tab completion for choices (default: True)

    Returns:
        Selected choice
    """
    # Validate inputs
    if not choices:
        raise ValueError("Cannot select from an empty list of choices")

    if default is not None and not (0 <= default < len(choices)):
        raise ValueError(f"Default index {default} is out of range for {len(choices)} choices")

    # Build the display
    prompt_str = f"\n{message}\n"
    for i, choice in enumerate(choices):
        marker = ">" if default == i else " "
        prompt_str += f"  {marker} {i + 1}. {choice}\n"

    default_str = str(default + 1) if default is not None else ""
    full_message = f"{prompt_str}\n{_ENTER_CHOICE_PROMPT} (1-{len(choices)}): "

    # Set up autocomplete for number strings (not choice text, since only
    # numeric input is accepted)
    completer = None
    if autocomplete:
        completer = WordCompleter([str(i + 1) for i in range(len(choices))])

    while True:
        try:
            user_input = prompt_toolkit.prompt(
                full_message,
                default=default_str,
                validator=_SelectionValidator(choices),
                completer=completer,
            ).strip()

            if not user_input and default is not None:
                choice = choices[default]
            elif user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(choices):
                    choice = choices[idx]
                else:
                    continue  # Validator should catch this
            else:
                continue

            if validator:
                result = validator(choice)
                if result is not None:
                    return result
            else:
                return choice

        except KeyboardInterrupt:
            raise
        except EOFError:
            raise


def multiselect(
    choices: list[str],
    message: str = _DEFAULT_MULTISELECT_MESSAGE,
    default: list[int] | None = None,
    validator: Callable[[list[str]], list[T] | None] | None = None,
) -> list[T] | list[str]:
    """
    Prompt user to select multiple choices.

    Args:
        choices: List of choices
        message: The prompt message
        default: Default indices (0-based)
        validator: Optional validator

    Returns:
        List of selected choices
    """
    # Validate inputs
    if not choices:
        raise ValueError("Cannot select from an empty list of choices")

    if default is not None:
        for idx in default:
            if not (0 <= idx < len(choices)):
                raise ValueError(f"Default index {idx} is out of range for {len(choices)} choices")

    # Build the display
    prompt_str = f"\n{message}\n"
    prompt_str += "(Enter numbers separated by commas, e.g., 1,3,5)\n"
    prompt_str += "(Press Enter to confirm)\n\n"

    for i, choice in enumerate(choices):
        marker = "x" if default and i in default else " "
        prompt_str += f"  [{marker}] {i + 1}. {choice}\n"

    full_message = f"{prompt_str}\n{_ENTER_CHOICES_PROMPT}: "

    while True:
        try:
            user_input = prompt_toolkit.prompt(full_message, default="").strip()

            if not user_input:
                # Use defaults if provided
                if default:
                    result_choices = [choices[i] for i in default]
                else:
                    result_choices = []

                if validator:
                    result = validator(result_choices)
                    if result is not None:
                        return result
                    print("Invalid selection, please try again.", file=sys.stderr)
                    continue
                return result_choices

            # Parse input
            try:
                indices = [int(x.strip()) - 1 for x in user_input.split(",")]
                selected = []
                for idx in indices:
                    if 0 <= idx < len(choices):
                        selected.append(choices[idx])
                    else:
                        print(f"Invalid choice: {idx + 1}", file=sys.stderr)
                        continue

                if validator:
                    result = validator(selected)
                    if result is not None:
                        return result
                    print("Invalid selection, please try again.", file=sys.stderr)
                    continue
                return selected
            except ValueError:
                print(_INVALID_FORMAT_MSG, file=sys.stderr)
                continue

        except KeyboardInterrupt:
            raise
        except EOFError:
            raise
