"""Command infrastructure for Clir."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, TypeVar

from clir.core.params import Param, ParamType
from clir.core.context import Context

F = TypeVar("F", bound=Callable[..., Any])

# Type conversion functions - optimized with dictionary lookup
_TYPE_CONVERTERS: dict[type, Callable[[str], Any]] = {
    int: lambda v: int(v),
    float: lambda v: float(v),
    bool: lambda v: v.lower() in ("true", "1", "yes"),
}


class Command:
    """Represents a CLI command."""

    def __init__(
        self,
        func: Callable[..., Any],
        name: str | None = None,
        help: str | None = None,
    ):
        self.func = func
        self.name = name or func.__name__
        self.help = help or func.__doc__
        self.params: list[Param] = []

    def add_param(self, param: Param) -> None:
        """Add a parameter to this command."""
        self.params.append(param)

    def get_params(self) -> list[Param]:
        """Get parameters in the order function expects: args first, then options."""
        args = [p for p in self.params if p.param_type.value == "argument"]
        options = [p for p in self.params if p.param_type.value == "option"]
        return args + options

    def _convert_type(self, value: str, param: Param) -> Any:
        """Convert string value to the expected type."""
        if value is None:
            return param.default

        # Already the right type
        if isinstance(value, param.type):
            return value

        # Use dictionary lookup for performance
        converter = _TYPE_CONVERTERS.get(param.type)
        if converter:
            try:
                return converter(value)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid value '{value}' for {param.name}: expected {param.type.__name__}"
                ) from e

        # Unknown type - return as string
        return value

    async def run(self, args: dict[str, Any], parent: Context | None = None) -> Any:
        """Run the command with parsed arguments."""
        # Create context
        ctx = Context(self.name, args, parent)

        # Get param order from function signature
        sig = inspect.signature(self.func)
        params_by_name = {p.name: p for p in self.params}

        # Check if function accepts a context parameter
        param_names = list(sig.parameters.keys())
        wants_context = "context" in param_names

        # Build list of params in function signature order (excluding context)
        ordered_params = []
        for param_name in param_names:
            if param_name == "context":
                continue
            if param_name in params_by_name:
                ordered_params.append(params_by_name[param_name])

        # Add any params not in signature
        for param in self.params:
            if param not in ordered_params:
                ordered_params.append(param)

        param_values = []
        missing_required = []
        for param in ordered_params:
            # Look up by param name, or short name as fallback
            value = args.get(param.name)
            if value is None and param.short:
                short_key = param.short.lstrip('-')
                value = args.get(short_key)
            if value is None:
                value = param.default
            # Enforce required validation
            if value is None and param.required:
                missing_required.append(f"--{param.name}" if param.short else param.name)
                continue
            # Convert type from string
            if isinstance(value, str):
                value = self._convert_type(value, param)
            if param.validator and value is not None:
                validated = param.validator(value)
                if validated is None:
                    raise ValueError(
                        f"Invalid value for '{param.name}': validation failed"
                    )
                value = validated
            param_values.append(value)

        if missing_required:
            raise ValueError(f"Missing required argument(s): {', '.join(missing_required)}")

        # Pass context if wanted (at the end, after other params)
        if wants_context:
            result = self.func(*param_values, ctx)
        else:
            result = self.func(*param_values)

        # Support async commands
        if asyncio.iscoroutine(result):
            result = await result

        return result

    def __repr__(self) -> str:
        return f"Command({self.name})"


def command(name: str | None = None, help: str | None = None) -> Callable[[F], Command]:
    """Decorator to register a function as a CLI command."""

    def decorator(func: F) -> Command:
        cmd = Command(func, name=name, help=help)
        # Attach command to function for later retrieval
        func._clir_command = cmd  # type: ignore
        return cmd  # type: ignore

    return decorator


def argument(
    name: str | None = None,
    *,
    type: type | None = None,
    default: Any = None,
    required: bool = False,
    help: str | None = None,
    validator: Callable[[Any], Any] | None = None,
) -> Callable[[F], F]:
    """Decorator to add an argument to a command."""

    def decorator(func: F) -> F:
        cmd: Command = getattr(func, "_clir_command", None)
        if cmd is None:
            # Create command if it doesn't exist
            cmd = Command(func)
            func._clir_command = cmd  # type: ignore

        param_name = name or _infer_param_name(func, len(cmd.params))
        # Infer type from signature if not provided
        inferred_type = type
        if inferred_type is None:
            inferred_type = _infer_param_type(func, param_name)
        param = Param(
            name=param_name,
            param_type=ParamType.ARGUMENT,
            type=inferred_type,
            default=default,
            required=required,
            help=help,
            validator=validator,
        )
        cmd.add_param(param)
        return func

    return decorator


def option(
    name: str | None = None,
    short: str | None = None,
    *,
    type: type | None = None,
    default: Any = None,
    required: bool = False,
    help: str | None = None,
    validator: Callable[[Any], Any] | None = None,
) -> Callable[[F], F]:
    """Decorator to add an option to a command."""

    def decorator(func: F) -> F:
        cmd: Command = getattr(func, "_clir_command", None)
        if cmd is None:
            cmd = Command(func)
            func._clir_command = cmd  # type: ignore

        # Convert --long-name to long_name
        opt_name = name
        if opt_name and opt_name.startswith("--"):
            opt_name = opt_name[2:].replace("-", "_")
        elif opt_name and opt_name.startswith("-"):
            opt_name = opt_name[1:].replace("-", "_")

        param_name = opt_name or _infer_param_name(func, len(cmd.params))
        # Infer type from signature if not provided
        inferred_type = type
        if inferred_type is None:
            inferred_type = _infer_param_type(func, param_name)
        param = Param(
            name=param_name,
            param_type=ParamType.OPTION,
            type=inferred_type,
            default=default,
            required=required,
            help=help,
            short=short,
            validator=validator,
        )
        cmd.add_param(param)
        return func

    return decorator


def _infer_param_name(func: Callable[..., Any], index: int) -> str:
    """Infer parameter name from function signature at given index.

    Args:
        func: The function to inspect
        index: The parameter index (0-based)

    Returns:
        The parameter name, or 'arg{index}' if not determinable
    """
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        # Skip 'self' if present
        if params and params[0].name == "self":
            params = params[1:]
        if index < len(params):
            return params[index].name
    except ValueError:
        pass

    return f"arg{index}"


def _infer_param_type(func: Callable[..., Any], param_name: str) -> type:
    """Infer parameter type from function signature annotation.

    Args:
        func: The function to inspect
        param_name: The parameter name to look up

    Returns:
        The parameter type if annotated, otherwise str
    """
    try:
        sig = inspect.signature(func)
        params = dict(sig.parameters)
        if param_name in params:
            param = params[param_name]
            if param.annotation is not inspect.Parameter.empty:
                return param.annotation
    except ValueError:
        pass

    return str  # Default to str
