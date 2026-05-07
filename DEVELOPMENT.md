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