"""Parameter types for CLI arguments and options."""

from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ParamType(Enum):
    """Parameter types for CLI arguments."""

    ARGUMENT = "argument"
    OPTION = "option"


class Param:
    """Represents a parameter (argument or option) for a command."""

    # Valid types for CLI parameters
    VALID_TYPES = (str, int, float, bool, Path)

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
        dest: str | None = None,
        multiple: bool = False,
        nargs: int | None = None,
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

        if nargs is not None and nargs < 1:
            raise ValueError(f"nargs must be >= 1, got {nargs}")
        if nargs is not None and param_type is ParamType.ARGUMENT:
            raise ValueError("nargs is only supported for options, not arguments")
        if multiple and param_type is ParamType.ARGUMENT:
            raise ValueError("multiple is only supported for options, not arguments")

        self.name = name
        self.param_type = param_type
        self.type = type
        self.default = default
        self.required = required
        self.help = help
        self.short = short
        self.validator = validator
        # dest is the Python parameter name the value binds to. It defaults to
        # name, but may differ when the CLI flag spelling is not a valid Python
        # identifier (e.g. flag --in binding to param in_path).
        self.dest = dest or name
        # multiple: option may be repeated; values are collected into a list.
        self.multiple = multiple
        # nargs: option consumes exactly this many values at once.
        self.nargs = nargs

    def __repr__(self) -> str:
        return f"Param({self.param_type.value} {self.name})"
