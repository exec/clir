"""Progress bar utilities."""

from rich.progress import SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, track
from typing import Any, Iterable

from clir.output.style import get_console


class Progress:
    """A progress bar context manager."""

    def __init__(
        self,
        description: str = "Processing...",
        show_percent: bool = True,
        show_speed: bool = False,
    ):
        """Initialize the progress bar.

        Args:
            description: Label shown next to the progress bar.
            show_percent: Show percentage in progress bar
            show_speed: Show speed (items/sec)
        """
        self.description = description
        self.show_percent = show_percent
        self.show_speed = show_speed
        self._progress: Any = None
        self._task_id: Any = None

    def __enter__(self) -> "Progress":
        """Start the progress bar display."""
        from rich.progress import Progress as RichProgress

        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
        ]

        if self.show_percent:
            columns.append(TaskProgressColumn())

        if self.show_speed:
            columns.append(SpeedColumn())

        columns.append(TimeRemainingColumn())

        self._progress = RichProgress(
            *columns,
            console=get_console(),
            expand=self.show_percent or self.show_speed,
        )
        self._progress.__enter__()
        self._task_id = self._progress.add_task(self.description, total=None)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop the progress bar display, propagating any exception."""
        if self._progress:
            self._progress.__exit__(exc_type, exc_val, exc_tb)

    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update progress."""
        if self._progress and self._task_id is not None:
            self._progress.update(self._task_id, advance=advance, **kwargs)

    def set_total(self, total: int) -> None:
        """Set total items."""
        if self._progress and self._task_id is not None:
            self._progress.update(self._task_id, total=total)

    @property
    def completed(self) -> int:
        """Get completed count."""
        if self._progress and self._task_id is not None:
            return self._progress.tasks[self._task_id].completed
        return 0

    @property
    def total(self) -> int:
        """Get total count."""
        if self._progress and self._task_id is not None:
            return self._progress.tasks[self._task_id].total or 0
        return 0

    @property
    def percent(self) -> float:
        """Get completion percentage (0-100)."""
        if self.total > 0:
            return (self.completed / self.total) * 100
        return 0.0

    @staticmethod
    def wrap(iterable: Iterable[Any], **kwargs: Any) -> Iterable[Any]:
        """Wrap an iterable with a progress bar."""
        return track(iterable, **kwargs)


def ansi_progress(
    current: int,
    total: int,
    width: int = 40,
    prefix: str = "",
    show_percentage: bool = True,
) -> str:
    """Generate an ANSI progress bar string.

    Args:
        current: Current progress value
        total: Total value
        width: Width of the progress bar
        prefix: Prefix text (e.g., "Downloading:")
        show_percentage: Whether to show percentage

    Returns:
        Formatted progress bar string
    """
    if total <= 0:
        percent = 0
    else:
        percent = min(100, max(0, int(current / total * 100)))

    filled = int(width * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (width - filled)

    if show_percentage:
        return f"{prefix}[{bar}] {percent}%"
    else:
        return f"{prefix}[{bar}]"


def print_ansi_progress(
    current: int,
    total: int,
    width: int = 40,
    prefix: str = "",
    show_percentage: bool = True,
) -> None:
    """Print an ANSI progress bar (overwrites current line).

    Args:
        current: Current progress value
        total: Total value
        width: Width of the progress bar
        prefix: Prefix text
        show_percentage: Whether to show percentage
    """
    import sys
    bar = ansi_progress(current, total, width, prefix, show_percentage)
    sys.stdout.write(f"\r{bar}")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()


import sys


def ansi_progress(
    current: int,
    total: int,
    width: int = 40,
    prefix: str = "",
) -> str:
    """Generate a simple ANSI progress bar string.

    Args:
        current: Current progress value
        total: Total value
        width: Width of the progress bar
        prefix: Prefix text

    Returns:
        Formatted progress bar string
    """
    if total <= 0:
        percent = 0
    else:
        percent = min(100, max(0, int(current / total * 100)))

    filled = int(width * current / total) if total > 0 else 0
    bar = "=" * filled + "-" * (width - filled)

    return f"{prefix}[{bar}] {percent}%"


def print_ansi_progress(
    current: int,
    total: int,
    width: int = 40,
    prefix: str = "",
) -> None:
    """Print an ANSI progress bar (overwrites current line).

    Args:
        current: Current progress value
        total: Total value
        width: Width of the progress bar
        prefix: Prefix text
    """
    bar = ansi_progress(current, total, width, prefix)
    sys.stdout.write(f"\r{bar}")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()


class ETA:
    """Estimate time of arrival calculator."""

    def __init__(self):
        self._start_time: float | None = None
        self._values: list[tuple[int, float]] = []  # (value, timestamp)

    def start(self) -> None:
        """Start tracking progress."""
        import time
        self._start_time = time.time()
        self._values = []

    def update(self, current: int) -> None:
        """Record progress update."""
        import time
        self._values.append((current, time.time()))

    def estimate(self, total: int) -> float | None:
        """Estimate remaining seconds.

        Args:
            total: Total value

        Returns:
            Estimated seconds remaining, or None if insufficient data
        """
        if not self._values or len(self._values) < 2:
            return None

        # Calculate rate from recent updates
        recent = self._values[-10:]  # Use last 10 samples
        if len(recent) < 2:
            return None

        start_val, start_time = recent[0]
        end_val, end_time = recent[-1]

        if end_val <= start_val:
            return None

        rate = (end_val - start_val) / (end_time - start_time)
        if rate <= 0:
            return None

        remaining = total - end_val
        return remaining / rate

    def format_eta(self, total: int) -> str:
        """Format ETA as human-readable string.

        Args:
            total: Total value

        Returns:
            Formatted ETA string (e.g., "1m 30s" or "Done")
        """
        seconds = self.estimate(total)
        if seconds is None:
            return "Calculating..."

        if seconds <= 0:
            return "Done"

        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
