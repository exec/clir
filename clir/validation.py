"""Pydantic validation for CLI arguments."""

from __future__ import annotations

from typing import Any, TypeVar, Generic, get_type_hints
from pydantic import BaseModel, Field, ValidationError

T = TypeVar("T", bound=BaseModel)


class CLIValidator(Generic[T]):
    """Validates CLI arguments using Pydantic models.

    Example:
        class Args(BaseModel):
            name: str = Field(description="Your name")
            age: int = Field(default=18, ge=0, description="Your age")
            verbose: bool = Field(default=False, description="Verbose output")

        validator = CLIValidator(Args)
        args = validator.parse(["--name", "Alice", "--age", "25"])
    """

    def __init__(self, model_class: type[T]):
        """Initialize with a Pydantic model class.

        Args:
            model_class: Pydantic BaseModel subclass
        """
        self.model_class = model_class

    def parse(self, args: list[str] | dict[str, Any] | None = None) -> T:
        """Parse arguments into validated model.

        Args:
            args: List of CLI args (["--name", "Alice"]) or dict

        Returns:
            Validated Pydantic model instance

        Raises:
            ValidationError: If args don't match model
        """
        if args is None:
            return self.model_class()

        if isinstance(args, list):
            # Convert list to dict
            parsed = self._parse_list(args)
            return self.model_class(**parsed)
        else:
            return self.model_class(**args)

    def _parse_list(self, args: list[str]) -> dict[str, Any]:
        """Convert CLI argument list to dict.

        Args:
            args: List like ["--name", "Alice", "--verbose"]

        Returns:
            Dict of parsed arguments
        """
        result: dict[str, Any] = {}
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                key = arg[2:].replace("-", "_")
                # Check if next arg is a value
                if i + 1 < len(args) and not args[i + 1].startswith("-"):
                    result[key] = self._convert_value(args[i + 1])
                    i += 2
                else:
                    result[key] = True
                    i += 1
            elif arg.startswith("-"):
                key = arg[1:].replace("-", "_")
                if i + 1 < len(args) and not args[i + 1].startswith("-"):
                    result[key] = self._convert_value(args[i + 1])
                    i += 2
                else:
                    result[key] = True
                    i += 1
            else:
                # Positional argument
                i += 1
        return result

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Try bool
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Try int
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        return value

    def validate(self, data: dict[str, Any]) -> T:
        """Validate a dict against the model.

        Args:
            data: Dict of arguments

        Returns:
            Validated model instance
        """
        return self.model_class(**data)

    @property
    def schema(self) -> dict[str, Any]:
        """Get JSON schema for the model."""
        return self.model_class.model_json_schema()

    def to_argparse(self) -> dict[str, Any]:
        """Convert model to argparse-compatible config.

        Returns:
            Dict with 'arguments' and 'options' lists
        """
        hints = get_type_hints(self.model_class)
        fields = self.model_class.model_fields

        arguments = []
        options = []

        for name, field in fields.items():
            field_info = {
                "name": name,
                "type": field.annotation,
                "default": field.default,
                "required": field.is_required(),
                "help": field.description or "",
            }

            # Check if it has short flag indicators
            if name.startswith("_") or field.default is not None:
                options.append(field_info)
            else:
                arguments.append(field_info)

        return {"arguments": arguments, "options": options}


def validator(model_class: type[T]) -> CLIValidator[T]:
    """Create a CLI validator from a Pydantic model.

    Args:
        model_class: Pydantic BaseModel subclass

    Returns:
        CLIValidator instance

    Example:
        class Args(BaseModel):
            name: str
            age: int = 18

        validate = validator(Args)
        args = validate.parse(["--name", "Bob"])
    """
    return CLIValidator(model_class)


__all__ = ["CLIValidator", "validator", "BaseModel", "Field", "ValidationError"]