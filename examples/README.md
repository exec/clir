# Clir Examples

Two standalone example CLIs that together demonstrate nearly every clir feature.

## Running the examples

```bash
cd examples/

# Task manager
python taskman.py --help
python taskman.py --version

# Developer tools
python devtools.py --help
python devtools.py --version
```

---

## taskman.py — Task Manager

A persistent task list stored in `~/.clir_taskman.json`.

| Feature | Where |
|---|---|
| `ClirApp(name, description, version)` | Top of file |
| `@app.command()` / `@argument()` / `@option()` | `add`, `list`, `done`, `remove`, `clear` |
| `@app.group()` + `@group.command()` | `tag` group, `theme` group |
| `Table(title, show_lines, box)` + chaining | `list`, `tag list` |
| `Panel(border_style)` — dynamic border | `show` |
| `Spinner` as context manager | `export` |
| `Progress(set_total, update)` | `export` |
| `Progress.wrap(iterable)` | `export` |
| `echo, success, error, warning, info, debug` | Throughout |
| `prompt(validator)` | `interactive` |
| `confirm(default)` | `done`, `remove`, `clear`, `interactive` |
| `select(choices, default)` | `interactive` |
| `multiselect(choices)` | `interactive` |
| `set_theme / get_theme / get_available_themes` | `theme set`, `theme list` |
| `get_terminal_capability()` | `theme list` |
| Context object (`context` parameter) | `show` |
| Async command (`async def`) | `export` |

### Quick tour

```bash
python taskman.py add "Buy groceries" --priority high --tag shopping
python taskman.py add "Read a book" --priority low
python taskman.py list
python taskman.py show 1
python taskman.py done 1
python taskman.py list --include-done
python taskman.py interactive
python taskman.py export --format json
python taskman.py tag add 2 personal
python taskman.py tag list 2
python taskman.py theme list
python taskman.py theme set dracula
python taskman.py clear
```

---

## devtools.py — Developer Tools

A developer utility with persistent config (`~/.clir_devtools.json`) and session (`~/.clir_devtools_session.json`).

| Feature | Where |
|---|---|
| Nested groups (`@group.group()`) | `auth token` (group inside group) |
| `Spinner` manual API (`start/stop/update`) | `info` |
| `Progress(set_total, update)` | `init` |
| `Progress.wrap(iterable)` | `scan` |
| `Panel` — green / red / cyan / yellow borders | `check`, `whoami`, `token create` |
| `Table(box, style, show_lines, min_width)` | `scan`, `config list` |
| `Table` with `double` / `double_edge` box | `config list`, `init` |
| `validate_path(path, base_dir)` | `scan` |
| `is_safe_path(path, base_dir)` | `scan`, `check` |
| `password()` | `auth login` |
| `confirm_password(min_length)` | `auth passwd` |
| `autocomplete(list)` → `WordCompleter` | `config interactive` |
| `autocomplete(callable)` → `DynamicCompleter` | `config interactive` |
| `prompt_input(completer=...)` | `config interactive` |
| `select()` + `multiselect(default=[...])` | `init` |

### Quick tour

```bash
# System info — Spinner manual API
python devtools.py info

# Path scanning — Progress.wrap + validate_path + is_safe_path
python devtools.py scan /tmp
python devtools.py scan /tmp --recursive --base /tmp

# Path safety check
python devtools.py check /tmp/safe
python devtools.py check /etc/passwd --base /tmp

# Config — autocomplete demo
python devtools.py config list
python devtools.py config set editor nano
python devtools.py config interactive    # Tab-completion in prompts
python devtools.py config reset

# Auth — password, confirm_password, nested token group
python devtools.py auth login
python devtools.py auth whoami
python devtools.py auth passwd              # confirm_password demo
python devtools.py auth token create --name ci-token --expires 7d
python devtools.py auth token revoke ci-token
python devtools.py auth logout

# Project init — select + multiselect + Progress
python devtools.py init --name myproject
```

---

## Feature coverage summary

| Category | Covered |
|---|---|
| Commands & groups | `@app.command`, `@app.group`, `@group.command`, `@group.group` (nested) |
| Parameters | `@argument(type, required, validator)`, `@option(short, default, help)` |
| Output helpers | `echo`, `success`, `error`, `warning`, `info`, `debug` |
| Table | title, box styles, show_lines, style, min_width, add_rows, chaining |
| Panel | content, title, border_style (green/red/cyan/yellow/blue) |
| Spinner | context manager, manual start/stop/update, custom spinner_name |
| Progress | set_total + update, `Progress.wrap(iterable)` |
| Themes | `set_theme`, `get_theme`, `get_available_themes`, `get_terminal_capability` |
| Prompts | `prompt` (validator), `password`, `confirm`, `select`, `multiselect`, `confirm_password` |
| Autocomplete | `autocomplete(list)` WordCompleter, `autocomplete(callable)` DynamicCompleter |
| Security | `validate_path`, `is_safe_path` |
| Async | `async def` command, `await` inside command |
| Context object | `context` parameter, `context.command_name`, `context.args` |
| Version flag | `--version` on both apps |
