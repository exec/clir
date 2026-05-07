"""Base prompt functionality."""

from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class Prompt(Generic[T]):
    """Base class for prompts, generic over the return type T."""

    def __init__(
        self,
        message: str,
        default: T | None = None,
        validator: Callable[[Any], T | None] | None = None,
    ):
        self.message = message
        self.default = default
        self.validator = validator
