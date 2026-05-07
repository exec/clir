"""Config file support for CLI applications.

Supports YAML, JSON, and TOML config files.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

from clir.errors import ClirError

# Optional imports - these are optional dependencies
_yaml_available = False
_toml_available = False

try:
    import yaml
    _yaml_available = True
except ImportError:
    pass

try:
    import tomli
    import tomli_w
    _toml_available = True
except ImportError:
    try:
        import toml as tomli
        import toml as tomli_w
        _toml_available = True
    except ImportError:
        pass


class ConfigError(ClirError):
    """Error loading or parsing config file."""
    pass


class ConfigLoader:
    """Load configuration from files."""

    SUPPORTED_FORMATS = {
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".toml": "toml",
    }

    DEFAULT_CONFIG_NAMES = [
        ".{app_name}rc",
        "{app_name}.config",
        "{app_name}.yaml",
        "{app_name}.yml",
        "{app_name}.json",
        "{app_name}.toml",
        ".{app_name}.yaml",
        ".{app_name}.yml",
        ".{app_name}.json",
        ".{app_name}.toml",
    ]

    def __init__(
        self,
        app_name: str,
        config_dir: str | Path | None = None,
        config_file: str | Path | None = None,
    ):
        """Initialize config loader.

        Args:
            app_name: Application name for config file discovery
            config_dir: Directory to search for config files
            config_file: Explicit config file path (bypasses discovery)
        """
        self.app_name = app_name
        self.config_dir = config_dir or _get_default_config_dir()
        self.config_file = config_file

    def _detect_format(self, file_path: Path) -> str | None:
        """Detect config format from file extension."""
        ext = file_path.suffix.lower()
        return self.SUPPORTED_FORMATS.get(ext)

    def _parse_yaml(self, content: str) -> dict[str, Any]:
        """Parse YAML content."""
        if not _yaml_available:
            raise ConfigError(
                "YAML support requires 'pyyaml' package. Install with: pip install pyyaml"
            )
        return yaml.safe_load(content) or {}

    def _parse_json(self, content: str) -> dict[str, Any]:
        """Parse JSON content."""
        return json.loads(content)

    def _parse_toml(self, content: str) -> dict[str, Any]:
        """Parse TOML content."""
        if not _toml_available:
            raise ConfigError(
                "TOML support requires 'tomli' package. Install with: pip install tomli"
            )
        return tomli.loads(content)

    def load(self, path: str | Path | None = None) -> dict[str, Any]:
        """Load configuration from file.

        Args:
            path: Explicit config file path. If None, uses config_file or discovers.

        Returns:
            Configuration dictionary

        Raises:
            ConfigError: If file not found or cannot be parsed
        """
        if path:
            config_path = Path(path)
        elif self.config_file:
            config_path = Path(self.config_file)
        else:
            config_path = self._discover_config()

        if not config_path or not config_path.exists():
            return {}

        format_type = self._detect_format(config_path)
        if not format_type:
            raise ConfigError(f"Unsupported config format: {config_path.suffix}")

        try:
            content = config_path.read_text(encoding="utf-8")
        except OSError as e:
            raise ConfigError(f"Cannot read config file: {e}") from e

        if format_type == "yaml":
            return self._parse_yaml(content)
        elif format_type == "json":
            return self._parse_json(content)
        elif format_type == "toml":
            return self._parse_toml(content)

        raise ConfigError(f"Unknown format: {format_type}")

    def _discover_config(self) -> Path | None:
        """Discover config file in standard locations.

        Search order:
        1. Explicit config_file if set
        2. Current working directory
        3. User home directory
        4. XDG config directory
        """
        # Try explicit config locations
        search_dirs = [
            Path.cwd(),
            Path.home(),
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")),
        ]

        for search_dir in search_dirs:
            for name_template in self.DEFAULT_CONFIG_NAMES:
                name = name_template.format(app_name=self.app_name)
                candidate = search_dir / name
                if candidate.exists():
                    return candidate

        return None


def load_config(
    path: str | Path | None = None,
    app_name: str | None = None,
    config_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load configuration from file.

    Args:
        path: Explicit config file path
        app_name: Application name (used for config discovery)
        config_dir: Directory to search for config files

    Returns:
        Configuration dictionary

    Examples:
        # Load explicit config file
        config = load_config("config.yaml")

        # Load with app name for auto-discovery
        config = load_config(app_name="myapp")

        # Load from specific directory
        config = load_config(app_name="myapp", config_dir="/etc/myapp")
    """
    if not app_name and not path:
        raise ConfigError("Either 'app_name' or 'path' must be provided")

    if not app_name and path:
        # Extract app_name from path for format detection
        app_name = Path(path).stem

    loader = ConfigLoader(
        app_name=app_name,
        config_dir=config_dir,
        config_file=path,
    )

    return loader.load()


def get_config(
    name: str | None = None,
    path: str | Path | None = None,
    config_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Get configuration with environment variable override.

    Environment variables take precedence over config file values.
    Prefix with uppercase app name (e.g., MYAPP_DEBUG=true).

    Args:
        name: Application name (used for env var prefix and config discovery)
        path: Explicit config file path
        config_dir: Directory to search for config files

    Returns:
        Configuration dictionary with env overrides applied
    """
    config = load_config(path=path, app_name=name, config_dir=config_dir)

    if name:
        prefix = f"{name.upper()}_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                config[config_key] = _parse_env_value(value)

    return config


def _parse_env_value(value: str) -> str | int | float | bool | None:
    """Parse environment variable value."""
    # Handle booleans
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False

    # Handle null/None
    if value.lower() in ("null", "none", ""):
        return None

    # Try numeric
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    return value


def save_config(
    config: dict[str, Any],
    path: str | Path,
    format: str = "auto",
) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save
        path: Output file path
        format: Output format (yaml, json, toml, auto)

    Raises:
        ConfigError: If format not supported or write fails
    """
    output_path = Path(path)

    if format == "auto":
        format = output_path.suffix.lstrip(".").lower()
        if format not in ("yaml", "yml", "json", "toml"):
            raise ConfigError(f"Cannot detect format from: {output_path}")

    try:
        if format in ("yaml", "yml"):
            if not _yaml_available:
                raise ConfigError("YAML support requires 'pyyaml' package")
            content = yaml.dump(config, default_flow_style=False)
        elif format == "json":
            content = json.dumps(config, indent=2)
        elif format == "toml":
            if not _toml_available:
                raise ConfigError("TOML support requires 'tomli' package")
            content = tomli_w.dumps(config)
        else:
            raise ConfigError(f"Unsupported format: {format}")

        output_path.write_text(content, encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"Cannot write config file: {e}") from e


def _get_default_config_dir() -> Path:
    """Get default config directory."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config)
    return Path.home() / ".config"


__all__ = [
    "ConfigLoader",
    "ConfigError",
    "load_config",
    "get_config",
    "save_config",
]