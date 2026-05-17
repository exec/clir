"""File glob expansion for CLI arguments."""

from __future__ import annotations

import glob as glob_module
import os
from pathlib import Path
from typing import Any


def expand_globs(args: list[str], base_dir: str | None = None) -> list[str]:
    """Expand glob patterns in command arguments.

    Args:
        args: List of command arguments
        base_dir: Base directory for relative globs

    Returns:
        Expanded list with glob patterns replaced by matching files

    Example:
        >>> expand_globs(['file.txt', '*.py', 'dir/*.json'])
        ['file.txt', 'main.py', 'utils.py', 'dir/config.json']
    """
    expanded = []
    base = Path(base_dir) if base_dir else Path.cwd()

    for arg in args:
        # Skip flags and their values
        if arg.startswith("-"):
            expanded.append(arg)
            continue

        # Check if it's a glob pattern
        if "*" in arg or "?" in arg or "[" in arg:
            try:
                # Expand relative to base_dir
                pattern = str(base / arg) if not os.path.isabs(arg) else arg
                matches = glob_module.glob(pattern)

                if matches:
                    # Sort for consistent ordering
                    matches.sort()
                    expanded.extend(matches)
                else:
                    # No matches, keep original
                    expanded.append(arg)
            except Exception:
                # On error, keep original
                expanded.append(arg)
        else:
            expanded.append(arg)

    return expanded


def expand_glob_single(pattern: str, base_dir: str | None = None) -> list[str]:
    """Expand a single glob pattern.

    Args:
        pattern: Glob pattern
        base_dir: Base directory

    Returns:
        List of matching files
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    full_pattern = str(base / pattern) if not os.path.isabs(pattern) else pattern
    matches = glob_module.glob(full_pattern)
    return sorted(matches) if matches else [pattern]


def is_glob(text: str) -> bool:
    """Check if a string contains glob patterns.

    Args:
        text: String to check

    Returns:
        True if contains glob characters
    """
    return any(c in text for c in "*?[")


def glob_files(
    *patterns: str,
    base_dir: str | None = None,
    recursive: bool = True,
) -> list[str]:
    """Expand multiple glob patterns.

    Args:
        *patterns: Glob patterns to expand
        base_dir: Base directory
        recursive: Use recursive glob (**)

    Returns:
        List of all matching files
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    all_files = []

    for pattern in patterns:
        full_pattern = str(base / pattern) if not os.path.isabs(pattern) else pattern

        if recursive and "**" not in pattern:
            # Recurse into subdirectories: insert a `**/` component before the
            # final path segment so e.g. `src/*.py` also matches `src/a/b.py`.
            # `glob` only treats `**` as recursive when it is a whole path
            # component, so the previous `*` -> `**` substitution did nothing
            # useful (it produced patterns like `**.py`).
            head, sep, tail = full_pattern.rpartition(os.sep)
            if sep:
                full_pattern = f"{head}{sep}**{sep}{tail}"
            else:
                full_pattern = f"**{os.sep}{full_pattern}"

        matches = glob_module.glob(full_pattern, recursive=recursive)
        all_files.extend(matches)

    return sorted(set(all_files))


__all__ = [
    "expand_globs",
    "expand_glob_single",
    "is_glob",
    "glob_files",
]