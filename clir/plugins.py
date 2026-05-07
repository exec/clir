"""Plugin system for extending CLI functionality."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable


class Plugin:
    """Base class for plugins."""

    name: str = "base"
    version: str = "0.1.0"

    def __init__(self, app: "PluginManager"):
        self.app = app

    def on_register(self) -> None:
        """Called when plugin is registered."""
        pass

    def on_command_register(self, command_name: str) -> None:
        """Called when a command is registered."""
        pass

    def on_before_run(self, command: str, args: dict[str, Any]) -> None:
        """Called before a command runs."""
        pass

    def on_after_run(self, command: str, args: dict[str, Any], result: Any) -> None:
        """Called after a command runs."""
        pass


class PluginManager:
    """Manage CLI plugins."""

    def __init__(self, app: Any = None):
        self.app = app
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin | type[Plugin]) -> None:
        """Register a plugin.

        Args:
            plugin: Plugin instance or class
        """
        if isinstance(plugin, type):
            plugin = plugin(self.app)

        self._plugins[plugin.name] = plugin
        plugin.on_register()

    def unregister(self, name: str) -> bool:
        """Unregister a plugin.

        Args:
            name: Plugin name

        Returns:
            True if unregistered
        """
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    def get(self, name: str) -> Plugin | None:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list(self) -> list[str]:
        """List all registered plugin names."""
        return list(self._plugins.keys())

    def load_from_file(self, path: str | Path) -> Plugin | None:
        """Load a plugin from a Python file.

        Args:
            path: Path to plugin file

        Returns:
            Loaded plugin or None
        """
        path = Path(path)

        if not path.exists():
            return None

        # Load module from file
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[path.stem] = module
        spec.loader.exec_module(module)

        # Find Plugin subclass
        for item in module.__dict__.values():
            if isinstance(item, type) and issubclass(item, Plugin) and item is not Plugin:
                plugin = item(self.app)
                self.register(plugin)
                return plugin

        return None

    def load_from_directory(self, dir_path: str | Path) -> list[Plugin]:
        """Load all plugins from a directory.

        Args:
            dir_path: Directory containing plugin files

        Returns:
            List of loaded plugins
        """
        dir_path = Path(dir_path)
        loaded = []

        for path in dir_path.glob("*.py"):
            if path.name.startswith("_"):
                continue
            plugin = self.load_from_file(path)
            if plugin:
                loaded.append(plugin)

        return loaded


def plugin(name: str | None = None) -> Callable[[type[Plugin]], type[Plugin]]:
    """Decorator to define a plugin.

    Args:
        name: Plugin name (defaults to class name)

    Example:
        @plugin("my_plugin")
        class MyPlugin(Plugin):
            pass
    """
    def decorator(cls: type[Plugin]) -> type[Plugin]:
        if name:
            cls.name = name
        return cls
    return decorator


__all__ = ["Plugin", "PluginManager", "plugin"]