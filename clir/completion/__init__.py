"""Shell completion generation for Clir CLI applications."""

from __future__ import annotations

import os
import sys
from typing import Any

from clir.core.command import Command
from clir.core.group import Group


def _escape_completion(text: str) -> str:
    """Escape special characters for shell completion."""
    return text.replace("'", "'\\''")


def _get_commands_recursive(
    commands: dict[str, Command | Group],
    prefix: str = "",
) -> list[tuple[str, str]]:
    """Recursively get all commands and groups with their descriptions."""
    result = []
    for name, cmd in commands.items():
        full_name = f"{prefix}{name}" if prefix else name
        desc = cmd.help or ""
        result.append((full_name, desc))
        if isinstance(cmd, Group):
            result.extend(_get_commands_recursive(cmd.commands, f"{full_name} "))
    return result


def _get_options(cmd: Command | Group) -> list[tuple[str, str, bool]]:
    """Get options for a command (name, help, is_flag)."""
    options = []
    if isinstance(cmd, Command):
        for param in cmd.params:
            if param.param_type.value == "option":
                opt_name = f"--{param.name.replace('_', '-')}"
                if param.short:
                    opt_name += f" -${param.short.lstrip('-')}"
                options.append((opt_name, param.help or "", param.type is bool))
    return options


def generate_bash_completion(app_name: str, commands: dict[str, Command | Group]) -> str:
    """Generate bash completion script.

    Args:
        app_name: Name of the CLI application
        commands: Dictionary of commands

    Returns:
        Bash completion script
    """
    # Get all commands
    all_commands = _get_commands_recursive(commands)
    cmd_list = " ".join(cmd[0].split()[0] for cmd in all_commands)

    script = f'''#!/bin/bash

_{app_name}_completion() {{
    local cur prev opts
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"

    # Top-level commands and groups
    opts="{cmd_list}"

    # Handle subcommands
    if [[ $COMP_CWORD -ge 2 ]]; then
        case "${{COMP_WORDS[1]}}" in
'''

    # Add completion for each command/group
    def add_cmd_completions(cmds: dict[str, Command | Group], indent: str = "                "):
        nonlocal script
        for name, cmd in cmds.items():
            if isinstance(cmd, Group):
                script += f'{indent}        {name})\n'
                script += f'{indent}            opts="${{opts}} $(compgen -W "${{__{app_name}_{name}_subcommands}}" -- "${{cur}}")"\n'
                script += f'{indent}            ;;\n'
                add_cmd_completions(cmd.commands, indent)
            elif isinstance(cmd, Command):
                opts_list = []
                for opt in _get_options(cmd):
                    opts_list.append(opt[0].split()[0])
                if opts_list:
                    script += f'{indent}        {name})\n'
                    script += f'{indent}            opts="${{opts}} $(compgen -W "{chr(32).join(opts_list)}" -- "${{cur}}")"\n'
                    script += f'{indent}            ;;\n'

    add_cmd_completions(commands)

    script += '''        esac
    fi

    COMPREPLY=($(compgen -W "$opts" -- "$cur"))
    return 0
}}

# Register completion
complete -F _''' + app_name + '''_completion ''' + app_name

    return script


def generate_zsh_completion(app_name: str, commands: dict[str, Command | Group]) -> str:
    """Generate zsh completion script.

    Args:
        app_name: Name of the CLI application
        commands: Dictionary of commands

    Returns:
        Zsh completion script
    """
    # Build command and option arrays
    cmd_lines = []
    opt_lines = []

    def process_commands(cmds: dict[str, Command | Group], indent: int = 0):
        indent_str = "    " * indent
        for name, cmd in cmds.items():
            if isinstance(cmd, Group):
                cmd_lines.append(f'{indent_str}"{name}"')
                process_commands(cmd.commands, indent + 1)
            else:
                cmd_lines.append(f'{indent_str}"{name}"')
                for opt in _get_options(cmd):
                    opt_name = opt[0].split()[0]
                    opt_lines.append(f'{indent_str}("{opt_name}[{opt[1]}]")')

    process_commands(commands)

    commands_str = "\n".join(cmd_lines)
    options_str = "\n".join(opt_lines) if opt_lines else ""

    if options_str:
        script = f'''#compdef {app_name}

local -a commands
commands=(
{commands_str}
)

local -a options
options=(
{options_str}
)

_arguments -C \\
    '1: :_guard "^-*" command' \\
    '*:: :->args' \\
    && return 0

case "$words[1]" in
'''
    else:
        script = f'''#compdef {app_name}

local -a commands
commands=(
{commands_str}
)

_arguments '1:command:($commands)' '*::arg:_dummy'

case "$words[1]" in
'''

    # Add case for each command
    def add_zsh_cases(cmds: dict[str, Command | Group]):
        nonlocal script
        for name, cmd in cmds.items():
            if isinstance(cmd, Group):
                script += f'    {name})\n'
                script += f'        _arguments "1:subcommand:(${{__{name}_subcommands}})"\n'
                script += '        ;;\n'
                add_zsh_cases(cmd.commands)
            elif isinstance(cmd, Command):
                opts = _get_options(cmd)
                if opts:
                    script += f'    {name})\n'
                    script += '        _arguments \\\n'
                    for opt in opts:
                        opt_name = opt[0].split()[0]
                        script += f'            "{opt_name}[{opt[1]}]" \\\n'
                    script += '        ;;\n'

    add_zsh_cases(commands)

    script += 'esac\n'

    return script


def generate_fish_completion(app_name: str, commands: dict[str, Command | Group]) -> str:
    """Generate fish completion script.

    Args:
        app_name: Name of the CLI application
        commands: Dictionary of commands

    Returns:
        Fish completion script
    """
    # Collect all commands and options
    cmd_list = []
    opt_map: dict[str, list[tuple[str, str]]] = {}

    def collect_commands(cmds: dict[str, Command | Group], prefix: str = ""):
        for name, cmd in cmds.items():
            full_name = f"{prefix}{name}" if prefix else name
            cmd_list.append(full_name)
            if isinstance(cmd, Command):
                opts = _get_options(cmd)
                if opts:
                    opt_map[full_name] = opts
            elif isinstance(cmd, Group):
                collect_commands(cmd.commands, f"{full_name} ")

    collect_commands(commands)

    cmd_str = "\n        ".join(f'"{c}"' for c in cmd_list)

    script = f'''# fish completion for {app_name} -*- shell-script -*-

function __fish_{app_name}_needs_command
    set -l cmd (commandline -opc)
    if [ (count $cmd) -eq 1 ]
        return 0
    end
    return 1
end

function __fish_{app_name}_use_command
    set -l cmd (commandline -opc)
    if [ (count $cmd) -eq 1 ]
        if contains -- $cmd[1] {cmd_str}
            return 0
        end
    end
    return 1
end

function __fish_{app_name}_commands
    {app_name} --help 2>/dev/null | string match -r '^    \\w+' | string trim
end

'''

    # Add completions for each command with options
    for cmd_name, opts in opt_map.items():
        func_name = cmd_name.replace("-", "_").replace(" ", "_")
        script += f'function __fish_{app_name}_{func_name}_options\n'
        script += '    set -l opts\n'
        for opt in opts:
            opt_name = opt[0].split()[0]
            desc = opt[1]
            if desc:
                script += f'    opts="$opts {opt_name}\'{_escape_completion(desc)}\'"'
            else:
                script += f'    opts="$opts {opt_name}"'
            script += '\n'
        script += '    printf "%s\\n" $opts\n'
        script += 'end\n\n'

    # Main completion function
    script += f'''complete -c {app_name} -f -n '__fish_{app_name}_needs_command' -a '({cmd_str})'

'''


    # Add command-specific completions
    for cmd_name in opt_map:
        func_name = cmd_name.replace("-", "_").replace(" ", "_")
        script += 'complete -c ' + app_name + ' -f -n "__fish_' + app_name + '_use_command ' + cmd_name + '" -a "(__fish_' + app_name + '_' + func_name + '_options)"\n\n'

    return script


def generate_completion(
    shell: str,
    commands: dict[str, Command | Group],
    app_name: str = "cli",
) -> str:
    """Generate shell completion script.

    Args:
        shell: Shell type ('bash', 'zsh', or 'fish')
        commands: Dictionary of commands from the app
        app_name: Name of the CLI application

    Returns:
        Shell completion script

    Raises:
        ValueError: If shell type is not supported
    """
    shell = shell.lower()
    if shell == "bash":
        return generate_bash_completion(app_name, commands)
    elif shell == "zsh":
        return generate_zsh_completion(app_name, commands)
    elif shell == "fish":
        return generate_fish_completion(app_name, commands)
    else:
        raise ValueError(f"Unsupported shell: {shell}. Use 'bash', 'zsh', or 'fish'.")


def detect_shell() -> str | None:
    """Detect the current shell.

    Returns:
        Shell name ('bash', 'zsh', 'fish') or None if unknown
    """
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        return "bash"
    elif "zsh" in shell:
        return "zsh"
    elif "fish" in shell:
        return "fish"
    return None


def print_completion(shell: str | None = None) -> None:
    """Print completion script to stdout for installation.

    Args:
        shell: Shell type. If None, auto-detect.
    """
    if shell is None:
        shell = detect_shell()

    if shell is None:
        print("Could not detect shell. Please specify: bash, zsh, or fish", file=sys.stderr)
        sys.exit(1)

    # This will be called after app is fully configured
    # The actual implementation will be via ClirApp.generate_completion()
    print(f"Use app.generate_completion('{shell}') to generate completions", file=sys.stderr)


__all__ = [
    "generate_completion",
    "generate_bash_completion",
    "generate_zsh_completion",
    "generate_fish_completion",
    "detect_shell",
    "print_completion",
]