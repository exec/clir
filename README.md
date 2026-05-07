# Clir

A modern CLI toolkit for building beautiful terminal applications in Python.

## Features

- **Command Framework** - Decorator-based command registration with type-annotated arguments
- **Rich Terminal Output** - Colored text, tables, panels, progress bars, and spinners
- **Interactive Prompts** - Text input, confirmation dialogs, and selection prompts
- **Type Inference** - Automatically infer argument types from function signatures
- **Async Support** - Commands can be async functions
- **Testing Utilities** - Built-in tools for testing CLI applications

## Installation

```bash
pip install clir
```

## Quick Start

```python
from clir import ClirApp, argument, option
from clir.output import success, error, Table

app = ClirApp(
    name="mycli",
    description="My awesome CLI",
)

@app.command()
@argument("name")
@option("--count", "-c", default=1)
def greet(name: str, count: int):
    """Greet someone warmly."""
    for _ in range(count):
        success(f"Hello, {name}!")

@app.command()
def status():
    """Show system status."""
    t = Table("Component", "Status")
    t.add_row("Database", "Connected")
    t.add_row("API", "Running")
    t.show()

if __name__ == "__main__":
    app.run()
```

## Output Functions

```python
from clir.output import success, error, warning, info, debug, Table, Panel

success("Operation completed!")  # Green bold
error("Something went wrong")     # Red bold
warning("Be careful")             # Yellow bold
info("Here's some info")          # Cyan
debug("Debug message")            # Dim

# Tables
t = Table("Name", "Age")
t.add_row("Alice", "30")
t.add_row("Bob", "25")
t.show()

# Panels
Panel("Content", title="My Panel").show()
```

## Interactive Prompts

```python
from clir.prompts import prompt, confirm, select

# Text input
name = prompt("What is your name?")

# Confirmation
if confirm("Continue?", default=True):
    print("Continuing!")

# Selection
choice = select("Choose:", ["Option 1", "Option 2", "Option 3"])
```

## Testing

```python
from clir import ClirApp
from clir.testing import CliRunner

app = ClirApp(name="test")

@app.command()
def hello():
    print("Hello!")

runner = CliRunner(app)
result = runner.invoke(["hello"])

assert result.exit_code == 0
assert "Hello" in result.output
```

## License

MIT
