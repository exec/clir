# Clir Development

## 12.1 Shell Completion Generation

**Status**: Complete ✓

Generate shell completion scripts (bash, zsh, fish) for Clir apps.

### Implementation

- Created `clir/completion/__init__.py` with completion generators
- Added `generate_completion()` and `print_completion()` methods to `ClirApp`
- Exported `generate_completion` and `detect_shell` from main `__init__.py`

### Files Modified

- `clir/completion/__init__.py` - New file with CompletionGenerator
- `clir/core/app.py` - Add `generate_completion()` and `print_completion()` methods
- `clir/__init__.py` - Export completion module

### API

```python
from clir import ClirApp, generate_completion

app = ClirApp(name="mycli")

# Generate completion script
bash_script = app.generate_completion("bash")
zsh_script = app.generate_completion("zsh")
fish_script = app.generate_completion("fish")

# Or use standalone function
from clir import generate_completion
script = generate_completion("bash", app.commands, "mycli")

# Print to stdout for installation
app.print_completion("bash")
```

### Installation

```bash
# Bash
mycli generate-completion bash > /etc/bash_completion.d/mycli

# Zsh
mycli generate-completion zsh > ~/.zsh/completions/_mycli

# Fish
mycli generate-completion fish > ~/.config/fish/completions/mycli.fish
```

---

## 12.2 Config File Support

**Status**: Complete ✓

Load settings from config files (YAML, JSON, TOML) with auto-discovery and environment variable overrides.

### Implementation

- Created `clir/config/__init__.py` with ConfigLoader, load_config, get_config, save_config
- Added `load_config()` method and `config` property to `ClirApp`
- Environment variables override config file values with `{APP_NAME_}` prefix

### Files Modified

- `clir/config/__init__.py` - New file with config loading support
- `clir/core/app.py` - Add `load_config()`, `config` property, `get_config_value()` method
- `clir/__init__.py` - Export config functions

### Dependencies

- `pyyaml` - For YAML support (optional)
- `tomli` - For TOML support (optional)

### API

```python
from clir import ClirApp, load_config, get_config, save_config, ConfigError

# Standalone functions
config = load_config("config.yaml")
config = load_config(app_name="myapp")  # Auto-discovers config
config = get_config("myapp")  # With env var overrides (MYAPP_DEBUG=true)

# ClirApp integration
app = ClirApp(name="myapp")
app.load_config()  # Auto-discovers and loads config
app.load_config("config.yaml")  # Load specific file

# Access config values
debug = app.get_config_value("debug", False)
print(app.config)  # Full config dict

# Save config
save_config({"debug": True}, "config.yaml", format="yaml")
```

### Config File Discovery

Searches in order:
1. Explicit path if provided
2. Current working directory
3. User home directory
4. XDG_CONFIG_HOME directory

Supported filenames (with `{app_name}` substituted):
- `.{app_name}rc`
- `{app_name}.config`
- `{app_name}.yaml`, `{app_name}.yml`, `{app_name}.json`, `{app_name}.toml`
- `.{app_name}.yaml`, `.{app_name}.yml`, `.{app_name}.json`, `.{app_name}.toml`

### Environment Variable Override

```bash
# Set env var to override config
export MYAPP_DEBUG=true
export MYAPP_PORT=8080

# Config file values are overridden by env vars
```

---

## 12.3 Command Aliases

**Status**: Complete ✓

Support for command shortcuts.

### Implementation

- Created `clir/aliases.py` with AliasManager class and @alias decorator
- Added `aliases` property and alias resolution to `ClirApp`

### Files Modified

- `clir/aliases.py` - New file with AliasManager and alias decorator
- `clir/core/app.py` - Add alias support to ClirApp
- `clir/__init__.py` - Export AliasManager

### API

```python
from clir import ClirApp
from clir.aliases import alias, AliasManager

# Method 1: Using @alias decorator
app = ClirApp(name="mycli")

@alias("hi")
@alias(["hello", "greet"])
@app.command()
def hello(name: str):
    """Say hello."""
    print(f"Hello, {name}!")

# Using app's alias manager
app.aliases.add("ls", "list")
app.aliases.add("rm", "remove")
app.aliases.add("config set", "configure")

# Resolve aliases
resolved = app.aliases.resolve("ls")  # Returns "list"
```

### Alias Resolution

When running CLI, aliases are resolved before command execution:
```bash
mycli hi World      # Runs: hello World
mycli ls            # Runs: list
mycli config set foo=bar  # Runs: configure foo=bar
```

---

## 12.4 Interactive Wizards

**Status**: Complete ✓

Step-by-step multi-page prompt flows.

### Implementation

- Created `clir/wizard.py` with Wizard and Step classes
- Added `wizard()` helper function
- Integrated with existing prompts (select, text input)

### Files Modified

- `clir/wizard.py` - New file with Wizard class
- `clir/__init__.py` - Export wizard and Wizard

### API

```python
from clir import wizard

results = (
    wizard("Project Setup")
    .add_step("name", "Project name?")
    .add_step("language", "Language?", choices=["Python", "JavaScript", "Go"])
    .add_step("database", "Use database?", choices=["Yes", "No"])
    .run()
)
# Returns: {"name": "...", "language": "...", "database": "..."}
```

---

## 12.5 Pydantic Validation (Planned)

Type-safe validation for command-line args with Pydantic.

---

## 12.6 Tree Output Component (Planned)

Rich tree output for displaying hierarchical data.

---

## 12.7 Repeatable Options

**Status**: Complete ✓

An option that may be passed more than once, with every value collected into a
list (argparse `action="append"`).

### Implementation

- Added `multiple` flag to `Param` (options only — raises `ValueError` on an argument)
- `@option(multiple=True)` registers the param; `_add_command_params` wires
  `action="append"` into argparse
- `Command._convert_type` converts each list element with the param's `type`
- Help rendering appends a `...` placeholder to the flag's metavar

### Files Modified

- `clir/core/params.py` - `multiple` attribute + argument guardrail
- `clir/core/command.py` - `multiple` kwarg on `@option`; per-element conversion
- `clir/core/app.py` - `action="append"` wiring
- `clir/help.py` - `...` metavar in option rendering

### API

```python
from clir import ClirApp, option

app = ClirApp(name="mycli")

@app.command()
@option("--salvage", multiple=True, default=None, help="Salvage file")
def assemble(salvage):
    # mycli assemble --salvage a.jsonl --salvage b.jsonl
    #   salvage == ["a.jsonl", "b.jsonl"]
    # mycli assemble
    #   salvage == None   (default; distinguishes "not passed")
    ...
```

Use `default=None` to distinguish "not passed" from "passed zero times". The
element type comes from `type=` (defaults to `str`) and converts each value.

---

## 12.8 Fixed-Arity (nargs) Options

**Status**: Complete ✓

An option that consumes exactly `N` values at once (argparse `nargs=N`).

### Implementation

- Added `nargs` attribute to `Param` (options only; must be `>= 1`)
- `@option(nargs=N)` registers the param; `_add_command_params` passes `nargs`
  to argparse
- The bound value is an `N`-element list; each element is type-converted
- `multiple=True` combined with `nargs` yields a list of `N`-element lists
- Help rendering repeats the metavar `N` times (e.g. `COMPARE COMPARE`)

### Files Modified

- `clir/core/params.py` - `nargs` attribute + validation
- `clir/core/command.py` - `nargs` kwarg on `@option`
- `clir/core/app.py` - `nargs` wiring
- `clir/help.py` - repeated metavar in option rendering

### API

```python
from clir import ClirApp, option

app = ClirApp(name="mycli")

@app.command()
@option("--compare", nargs=2, default=None, help="Two models to compare")
def evaluate(compare):
    # mycli evaluate --compare modelA modelB
    #   compare == ["modelA", "modelB"]
    ...
```

Passing too few values raises an argparse error and exits non-zero.

---

## 12.9 Dest-Aliasing and Path-Typed Parameters

**Status**: Complete ✓

Two related parameter improvements.

**Dest-aliasing** lets the CLI flag spelling differ from the Python parameter
name — required when the natural flag name is a Python keyword (`--in`,
`--class`). **Path support** adds `pathlib.Path` as a first-class param type.

### Implementation

- Added `dest` attribute to `Param`; defaults to `name`. `Command.run` keys
  params by `dest` for signature binding and value lookup
- `@option`/`@argument` accept a `dest` kwarg; type inference resolves against
  `dest` when the signature parameter differs from the flag name
- argparse: options register with an explicit `dest`; positionals register
  under `dest` with `metavar` set to the CLI name
- Added `Path` to `Param.VALID_TYPES` and to `command._TYPE_CONVERTERS`
- Missing-required-option errors now report the `--flag` spelling, not the dest

### Files Modified

- `clir/core/params.py` - `dest` attribute, `Path` in `VALID_TYPES`
- `clir/core/command.py` - `dest` kwarg, `dest`-keyed binding, `Path` converter
- `clir/core/app.py` - explicit argparse `dest`/`metavar`, `--flag` error message
- `clir/help.py` - flag spelling rendered, not the dest

### API

```python
from pathlib import Path
from clir import ClirApp, argument, option

app = ClirApp(name="mycli")

@app.command()
@option("--in", dest="in_path", help="Input file")     # flag --in -> param in_path
@option("--out", type=Path, default=None)              # function receives a Path
@argument("class", dest="class_name")                  # positional, keyword-safe param
def triage(class_name, in_path, out):
    ...
```

---

## 12.10 Literal Brackets in Help Text

**Status**: Complete ✓

Author-supplied description and help prose is plain text, not rich markup.
Literal square brackets — `[options]`, `[FILE...]`, `[default: x]` — now render
verbatim instead of being silently swallowed by rich's markup parser.

### Implementation

- `clir/help.py` wraps every author-supplied string (`app.description`,
  `group.help`, `cmd.help`, `param.help`) and clir's own bracketed usage
  placeholders (`[command]`, `[options]`) in `rich.markup.escape()` before
  printing. Only clir's deliberate `[bold]`/`[yellow]` style tags remain
  live markup.

### Files Modified

- `clir/help.py` - escape author prose and bracketed usage placeholders

### Notes

Markup in help text is therefore opt-out by default — authors who genuinely
want styled help must pre-style with their own `rich` console. This matches
the principle that user-provided strings should render literally.

---

## 12.11 Usage Errors Exit With Code 2

**Status**: Complete ✓

Bad CLI input — a missing required argument/option, a value that fails its
validator, or an unknown command — is a *usage* error, not a runtime crash.
Such errors now exit with code 2 (matching argparse and POSIX convention) and
render as a clean one-line message, with no `ValueError:` prefix and no
"Run with --debug" traceback hint.

### Implementation

- `clir/core/command.py` — `Command.run` raises `UsageError` (exit 2) instead
  of a bare `ValueError` for missing required params and for the validator
  "validation failed" case. `_handle_exception` already special-cases
  `ClirError` (UsageError's base) → styled message + `exc.exit_code`.
- `clir/core/app.py` — the unknown-command and unknown-subcommand paths, and
  the "group invoked with no subcommand" path, exit 2 instead of 1. The
  "did you mean" suggestion is preserved.

### Files Modified

- `clir/core/command.py` - raise `UsageError` for missing args / bad values
- `clir/core/app.py` - exit 2 on unknown command / missing subcommand

### Notes

Runtime errors from inside a command body still exit 1 (or the `exit_code` of
a `ClirError` the command raises). Exit 2 is reserved for input the user can
fix by correcting the command line.
