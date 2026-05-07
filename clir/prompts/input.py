"""Text input prompt."""

from typing import Callable, TypeVar, Any, Union

import prompt_toolkit
from prompt_toolkit.completion import Completer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

T = TypeVar("T")


def prompt_input(
    message: str,
    default: str | None = None,
    validator: Callable[[str], T | None] | None = None,
    password: bool = False,
    completer: Completer | None = None,
) -> T | str:
    """
    Prompt for text input.

    Args:
        message: The prompt message
        default: Default value if user presses enter
        validator: Optional validator function
        password: Whether to mask input
        completer: Optional autocomplete completer

    Returns:
        The user's input
    """
    default_str = f" ({default})" if default else ""

    while True:
        try:
            if password:
                user_input = prompt_toolkit.prompt(
                    f"{message}{default_str}: ",
                    is_password=True,
                )
            else:
                user_input = prompt_toolkit.prompt(
                    f"{message}{default_str}: ",
                    default=default or "",
                )

            # Use default if input is empty and default exists
            if not user_input and default:
                user_input = default

            # Validate if validator provided
            if validator:
                result = validator(user_input)
                if result is not None:
                    return result
                print("Invalid input, please try again.")
            else:
                return user_input

        except KeyboardInterrupt:
            raise
        except EOFError:
            raise


def prompt_confirm(message: str, default: bool = False) -> bool:
    """
    Prompt for yes/no confirmation.

    Args:
        message: The prompt message
        default: Default value

    Returns:
        True for yes, False for no
    """
    default_str = " [Y/n]" if default else " [y/N]"
    bindings = KeyBindings()

    @bindings.add("y")
    def _yes(event: Any) -> None:
        event.app.exit(result=True)

    @bindings.add("n")
    def _no(event: Any) -> None:
        event.app.exit(result=False)

    @bindings.add(Keys.Enter)
    def _default(event: Any) -> None:
        event.app.exit(result=default)

    result = prompt_toolkit.prompt(
        f"{message}{default_str}: ",
        key_bindings=bindings,
        default="" if default else "",
    )

    # Key bindings may cause prompt() to return a bool directly
    if isinstance(result, bool):
        return result
    return result.lower() in ("y", "yes", "true") if result.strip() else default


# Convenience functions matching the planned API
def text(
    message: str,
    default: str | None = None,
    validator: Callable[[str], T | None] | None = None,
    completer: Completer | None = None,
) -> T | str:
    """Prompt for text input."""
    return prompt_input(message, default=default, validator=validator, completer=completer)


def password(
    message: str = "Password",
    validator: Callable[[str], T | None] | None = None,
) -> T | str:
    """Prompt for password input."""
    return prompt_input(message, password=True, validator=validator)


def confirm(
    message: str,
    default: bool = False,
) -> bool:
    """Prompt for yes/no confirmation."""
    return prompt_confirm(message, default=default)


def confirm_password(
    message: str = "Enter password",
    confirm_message: str = "Confirm password",
    min_length: int = 0,
) -> str:
    """Prompt for password confirmation.

    Args:
        message: The first password prompt message
        confirm_message: The confirmation prompt message
        min_length: Minimum required password length

    Returns:
        The confirmed password

    Raises:
        ValueError: If passwords don't match or are too short
    """
    while True:
        password = prompt_input(message, password=True)
        if min_length > 0 and len(password) < min_length:
            print(f"Password must be at least {min_length} characters.")
            continue

        if password:
            confirmed = prompt_input(confirm_message, password=True)
            if password == confirmed:
                return password
            print("Passwords do not match. Please try again.")
        else:
            print("Password cannot be empty.")


# Keep old names as aliases for backwards compatibility
prompt = text
