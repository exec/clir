"""Spinner/status utilities."""

from typing import Any

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner as RichSpinner

from clir.output.style import get_console


class Spinner:
    """A spinner for showing ongoing activity."""

    def __init__(self, message: str = "Loading...", spinner_name: str = "dots"):
        self.message = message
        self.spinner_name = spinner_name
        self._spinner: RichSpinner | None = None
        self._live: Live | None = None
        self._started = False

    def __enter__(self) -> "Spinner":
        """Start the spinner and return self."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop the spinner, propagating any exception."""
        self.stop()

    def start(self) -> None:
        """Start the spinner (can be used without context manager)."""
        if self._started:
            return
        self._spinner = RichSpinner(self.spinner_name, text=self.message)
        self._live = Live(
            self._spinner,
            console=get_console(),
            transient=True,
            refresh_per_second=20,
        )
        self._live.__enter__()
        self._started = True

    def stop(self) -> None:
        """Stop the spinner (can be used without context manager)."""
        if not self._started:
            return
        if self._live:
            self._live.__exit__(None, None, None)
        self._started = False

    def update(self, message: str | None = None) -> None:
        """Update the spinner message."""
        if message:
            self.message = message
        if self._spinner and self._live:
            self._spinner.text = self.message
            self._live.refresh()


def status(message: str) -> "Spinner":
    """Create a spinner with the given message."""
    return Spinner(message)
