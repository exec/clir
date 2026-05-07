"""Clir - A modern CLI toolkit for building beautiful terminal applications."""

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
from pydantic import BaseModel, Field, ValidationError

__version__ = "0.1.0"

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
]
