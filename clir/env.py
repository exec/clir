"""Environment variable expansion in CLI arguments."""

from __future__ import annotations

import os
import re
from typing import Any


def expand_env_vars(args: list[str]) -> list[str]:
    """Expand environment variables in arguments.

    Supports both $VAR and ${VAR} syntax.

    Args:
        args: List of command arguments

    Returns:
        Expanded list with environment variables replaced

    Example:
        >>> expand_env_vars(['$HOME/file.txt', '${USER}/data'])
        ['/home/user/file.txt', 'username/data']
    """
    expanded = []

    for arg in args:
        # Skip flags and their values
        if arg.startswith("-"):
            expanded.append(arg)
            continue

        # Check for environment variable references
        if "$" in arg:
            # Handle ${VAR} syntax
            arg = os.path.expandvars(arg)
            # Handle $VAR syntax (basic)
            for match in re.finditer(r'\$(\w+)', arg):
                var_name = match.group(1)
                value = os.environ.get(var_name, match.group(0))
                arg = arg.replace(f"${var_name}", value, 1)

        expanded.append(arg)

    return expanded


def expand_env_vars_in_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Expand environment variables in a dictionary.

    Args:
        data: Dictionary with string values

    Returns:
        Dictionary with expanded variables
    """
    result = {}

    for key, value in data.items():
        if isinstance(value, str) and "$" in value:
            result[key] = os.path.expandvars(value)
        elif isinstance(value, dict):
            result[key] = expand_env_vars_in_dict(value)
        elif isinstance(value, list):
            result[key] = [
                os.path.expandvars(v) if isinstance(v, str) and "$" in v else v
                for v in value
            ]
        else:
            result[key] = value

    return result


def get_env(key: str, default: str | None = None) -> str:
    """Get environment variable with expansion.

    Args:
        key: Variable name
        default: Default if not set

    Returns:
        Expanded value or default
    """
    value = os.environ.get(key, default)
    if value and "$" in value:
        return os.path.expandvars(value)
    return value or ""


def set_env(key: str, value: str) -> None:
    """Set environment variable.

    Args:
        key: Variable name
        value: Value to set
    """
    os.environ[key] = value


def list_env(prefix: str | None = None) -> dict[str, str]:
    """List environment variables, optionally filtered by prefix.

    Args:
        prefix: Filter by prefix (e.g., "MYAPP_")

    Returns:
        Dict of matching variables
    """
    if prefix:
        return {k: v for k, v in os.environ.items() if k.startswith(prefix)}
    return dict(os.environ)


__all__ = [
    "expand_env_vars",
    "expand_env_vars_in_dict",
    "get_env",
    "set_env",
    "list_env",
]