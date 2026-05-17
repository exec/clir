"""Clir - A modern CLI toolkit for building beautiful terminal applications."""

from importlib.metadata import PackageNotFoundError, version

from clir.core.app import ClirApp, main
from clir.core.command import command, argument, option
from clir.core.group import group
from clir.output import (
    echo,
    success,
    error,
    warning,
    info,
    debug,
    Table,
    Progress,
    Panel,
    Spinner,
)
from clir.prompts import prompt, password, confirm, confirm_password, select, multiselect, autocomplete
from clir.completion import generate_completion, detect_shell
from clir.config import load_config, get_config, save_config, ConfigError
from clir.validation import CLIValidator, validator
from clir.errors import ClirError, UsageError
from pydantic import BaseModel, Field, ValidationError

# Version comes from the installed package metadata, which setuptools reads
# from pyproject.toml — the single source of truth. The publish workflow also
# asserts the release tag matches it. Falls back when run from an uninstalled
# source tree.
try:
    __version__ = version("pyclir")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"

__all__ = [
    # Core
    "ClirApp",
    "main",
    "command",
    "group",
    "argument",
    "option",
    # Output
    "echo",
    "success",
    "error",
    "warning",
    "info",
    "debug",
    "Table",
    "Progress",
    "Panel",
    "Spinner",
    # Prompts
    "prompt",
    "password",
    "confirm",
    "confirm_password",
    "select",
    "multiselect",
    "autocomplete",
    # Completion
    "generate_completion",
    "detect_shell",
    # Config
    "load_config",
    "get_config",
    "save_config",
    "ConfigError",
    # Wizard
    "wizard",
    "Wizard",
    # Validation
    "CLIValidator",
    "validator",
    "ValidationError",
    "BaseModel",
    "Field",
    "ClirError",
    "UsageError",
]
