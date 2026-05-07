"""Parameter types for CLI arguments and options."""

from enum import Enum
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ParamType(Enum):
    """Parameter types for CLI arguments."""

    ARGUMENT = "argument"
    OPTION = "option"


class Param:
    """Represents a parameter (argument or option) for a command."""

    # Valid types for CLI parameters
    VALID_TYPES = (str, int, float, bool)

    def __init__(
        self,
        name: str,
        param_type: ParamType,
        type: type[T] = str,
        default: Any = None,
        required: bool = False,
        help: str | None = None,
        short: str | None = None,
        validator: Callable[[Any], T] | None = None,
    ):
        # Validate type parameter
        if not callable(type):
            raise TypeError(f"Param type must be callable, got {type!r}")
        if type not in self.VALID_TYPES and not (
            hasattr(type, '__origin__') or hasattr(type, '__args__')
        ):
            raise TypeError(
                f"Param type must be one of {self.VALID_TYPES} or a generic type, got {type!r}"
            )

        self.name = name
        self.param_type = param_type
        self.type = type
        self.default = default
        self.required = required
        self.help = help
        self.short = short
        self.validator = validator

    def __repr__(self) -> str:
        return f"Param({self.param_type.value} {self.name})"
