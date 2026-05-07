"""Interactive wizard for multi-step CLI flows."""

from __future__ import annotations

from typing import Any, Callable
from clir.prompts.input import prompt_input, confirm
from clir.prompts.select import select


class Step:
    """A single step in an interactive wizard."""

    def __init__(
        self,
        name: str,
        prompt: str,
        handler: Callable[[Any], Any],
        choices: list[str] | None = None,
        default: Any = None,
        validator: Callable[[Any], Any | None] | None = None,
    ):
        self.name = name
        self.prompt = prompt
        self.handler = handler
        self.choices = choices
        self.default = default
        self.validator = validator


class Wizard:
    """Multi-step interactive wizard."""

    def __init__(self, title: str, description: str | None = None):
        self.title = title
        self.description = description
        self.steps: list[Step] = []
        self.results: dict[str, Any] = {}

    def add_step(
        self,
        name: str,
        prompt: str,
        handler: Callable[[Any], Any] | None = None,
        choices: list[str] | None = None,
        default: Any = None,
        validator: Callable[[Any], Any | None] | None = None,
    ) -> "Wizard":
        """Add a step to the wizard.

        Args:
            name: Step identifier
            prompt: Question/prompt to show
            handler: Optional function to process input
            choices: If provided, use select instead of text input
            default: Default value
            validator: Optional validation function

        Returns:
            Self for chaining
        """
        self.steps.append(Step(name, prompt, handler, choices, default, validator))
        return self

    def run(self) -> dict[str, Any]:
        """Run the wizard interactively.

        Returns:
            Dictionary of results keyed by step name
        """
        print(f"\n{'=' * 50}")
        print(f"  {self.title}")
        print(f"{'=' * 50}")

        if self.description:
            print(f"\n{self.description}\n")

        for i, step in enumerate(self.steps, 1):
            print(f"\nStep {i}/{len(self.steps)}: {step.name}")

            try:
                if step.choices:
                    # Use selection prompt
                    value = select(
                        choices=step.choices,
                        message=step.prompt,
                        default=step.default,
                    )
                else:
                    # Use text input
                    value = prompt_input(
                        message=step.prompt,
                        default=step.default,
                        validator=step.validator,
                    )

                # Apply handler if provided
                if step.handler:
                    value = step.handler(value)

                self.results[step.name] = value

            except (KeyboardInterrupt, EOFError):
                print("\n\nWizard cancelled.")
                return {}

        print(f"\n{'=' * 50}")
        print("  Wizard Complete!")
        print(f"{'=' * 50}\n")

        return self.results


def wizard(
    title: str,
    description: str | None = None,
) -> Wizard:
    """Create an interactive wizard.

    Args:
        title: Wizard title
        description: Optional description

    Returns:
        Wizard instance

    Examples:
        results = (
            wizard("Setup Project")
            .add_step("name", "Project name?")
            .add_step("language", "Language?", choices=["Python", "JavaScript", "Go"])
            .add_step("db", "Use database?", choices=["Yes", "No"])
            .run()
        )
    """
    return Wizard(title, description)


__all__ = ["Wizard", "Step", "wizard"]