# Clir

A modern CLI toolkit for building beautiful terminal applications in Python.

## Features

- **Command Framework** - Decorator-based command registration with type-annotated arguments
- **Advanced Options** - Repeatable options, fixed-arity options, and flag-to-parameter aliasing
- **Rich Terminal Output** - Colored text, tables, panels, progress bars, and spinners
- **Interactive Prompts** - Text input, confirmation dialogs, and selection prompts
- **Type Inference** - Automatically infer argument types from function signatures
- **Async Support** - Commands can be async functions
- **Testing Utilities** - Built-in tools for testing CLI applications

## Installation

```bash
pip install pyclir
```

`pyclir` is the PyPI distribution name; the import package is `clir`
(`import clir`). The name `clir` was already taken on PyPI.

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

## Advanced Options

`@option` supports repeatable options, fixed-arity options, and binding a flag
to a differently-named Python parameter.

```python
from pathlib import Path
from clir import ClirApp, argument, option

app = ClirApp(name="mycli")

@app.command()
# Repeatable: pass --salvage more than once; values collect into a list.
@option("--salvage", multiple=True, default=None, help="Salvage file (repeatable)")
# Fixed-arity: --compare A B consumes exactly two values.
@option("--compare", nargs=2, default=None, help="Two models to compare")
# dest-aliasing: the CLI flag is --in, the function parameter is in_path.
@option("--in", dest="in_path", help="Input file")
# pathlib.Path is a supported type; the function receives a Path.
@option("--out", type=Path, default=None, help="Output path")
def run(salvage, compare, in_path, out):
    # mycli run --salvage a.jsonl --salvage b.jsonl --compare m1 m2 --in data.txt
    #   salvage == ["a.jsonl", "b.jsonl"]   (None when not passed)
    #   compare == ["m1", "m2"]             (None when not passed)
    #   in_path == "data.txt"
    ...
```

- **`multiple=True`** — the option may be passed repeatedly; every value is
  collected into a list. Use `default=None` to distinguish "not passed" from
  "passed empty".
- **`nargs=N`** — the option consumes exactly `N` values at once; the bound
  value is an `N`-element list. Combine with `multiple=True` for a list of
  fixed-length lists.
- **`dest="..."`** — binds the option (or argument) to a Python parameter whose
  name differs from the flag spelling — useful when the flag would be a Python
  keyword (`--in`, `--class`). Works on `@argument` too.
- **`type=`** — `str`, `int`, `float`, `bool`, and `pathlib.Path` are all
  supported; for list-valued options the type converts each element.

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
