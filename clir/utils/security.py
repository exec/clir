"""Security utilities for CLI applications."""

from pathlib import Path


def validate_path(path: str, base_dir: str | None = None) -> Path:
    """Validate a path to prevent directory traversal attacks.

    Args:
        path: The path to validate
        base_dir: Optional base directory to restrict access to

    Returns:
        The resolved Path object

    Raises:
        ValueError: If the path attempts directory traversal
        FileNotFoundError: If the path doesn't exist (when checking)
    """
    # Resolve the path
    resolved = Path(path).resolve()

    # If base_dir is provided, ensure the path is within it
    if base_dir:
        base = Path(base_dir).resolve()
        try:
            resolved.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Path '{path}' is outside the allowed directory '{base_dir}'"
            )

    return resolved


def is_safe_path(path: str, base_dir: str | None = None) -> bool:
    """Check if a path is safe (doesn't traverse directories).

    Args:
        path: The path to check
        base_dir: Optional base directory to restrict access to

    Returns:
        True if the path is safe, False otherwise
    """
    try:
        validate_path(path, base_dir)
        return True
    except (ValueError, FileNotFoundError):
        return False
