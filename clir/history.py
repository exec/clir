"""Command history persistence for CLI apps."""

from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any


class History:
    """Persistent command history."""

    def __init__(
        self,
        app_name: str,
        max_entries: int = 100,
        history_dir: str | Path | None = None,
    ):
        """Initialize history.

        Args:
            app_name: Application name for history file naming
            max_entries: Maximum history entries to keep
            history_dir: Directory for history file (default: XDG_DATA_HOME)
        """
        self.app_name = app_name
        self.max_entries = max_entries

        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                self.history_dir = Path(xdg_data)
            else:
                self.history_dir = Path.home() / ".local" / "share"

        self.history_file = self.history_dir / f".{app_name}_history"
        self._entries: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load history from file."""
        if not self.history_file.exists():
            return

        try:
            content = self.history_file.read_text(encoding="utf-8")
            self._entries = json.loads(content)
        except (json.JSONDecodeError, OSError):
            self._entries = []

    def save(self) -> None:
        """Save history to file."""
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(
                json.dumps(self._entries, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass  # Silently fail if we can't write

    def add(self, command: str, args: list[str] | None = None, timestamp: str | None = None) -> None:
        """Add an entry to history.

        Args:
            command: Command name
            args: Command arguments
            timestamp: Optional timestamp (default: now)
        """
        entry = {
            "command": command,
            "args": args or [],
            "timestamp": timestamp or datetime.now().isoformat(),
        }

        # Avoid duplicates (don't add same command twice in a row)
        if self._entries and self._entries[-1] == entry:
            return

        self._entries.append(entry)

        # Trim to max entries
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]

        self.save()

    def get(self, limit: int | None = None, command: str | None = None) -> list[dict[str, Any]]:
        """Get history entries.

        Args:
            limit: Limit number of entries
            command: Filter by command name

        Returns:
            List of history entries
        """
        entries = self._entries

        if command:
            entries = [e for e in entries if e["command"] == command]

        if limit:
            entries = entries[-limit:]

        return entries

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search history for query.

        Args:
            query: Search query

        Returns:
            Matching entries
        """
        query_lower = query.lower()
        return [
            e for e in self._entries
            if query_lower in e["command"].lower()
            or any(query_lower in str(a).lower() for a in e.get("args", []))
        ]

    def clear(self) -> None:
        """Clear all history."""
        self._entries.clear()
        self.save()

    def last(self, n: int = 1) -> list[dict[str, Any]]:
        """Get last N entries.

        Args:
            n: Number of entries

        Returns:
            Last N entries
        """
        return self._entries[-n:] if self._entries else []

    def commands(self) -> list[str]:
        """Get list of unique commands in history."""
        return list(dict.fromkeys(e["command"] for e in self._entries))


def history(
    app_name: str,
    max_entries: int = 100,
    history_dir: str | Path | None = None,
) -> History:
    """Create a history instance.

    Args:
        app_name: Application name
        max_entries: Maximum entries to keep
        history_dir: History directory

    Returns:
        History instance
    """
    return History(app_name, max_entries, history_dir)


__all__ = ["History", "history"]