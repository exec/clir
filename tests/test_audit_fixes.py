"""Regression tests for bugs found in the code audit.

Each test here pins a specific defect that was fixed:
  - the bare ``@command()`` decorator silently discarding stacked params
  - ``_convert_scalar`` crashing on parameterized-generic param types
  - ``glob_files(recursive=True)`` failing to recurse into subdirectories
"""

import asyncio

from clir.core.command import command, argument, option
from clir.core.command import Command
from clir.core.params import Param, ParamType
from clir.glob import glob_files


# --- bare @command() must keep stacked @argument/@option params -------------


def test_bare_command_decorator_keeps_stacked_params():
    """`@command()` over `@option`/`@argument` must reuse the pending Command.

    Previously `command()` always built a fresh Command, discarding every
    param that the inner decorators had registered.
    """

    @command()
    @argument("name")
    @option("--loud")
    def greet(name, loud=False):
        return (name, loud)

    assert isinstance(greet, Command)
    param_names = {p.name for p in greet.params}
    assert param_names == {"name", "loud"}


def test_bare_command_decorator_runs_with_params():
    @command()
    @argument("name")
    def greet(name):
        return f"hi {name}"

    assert asyncio.run(greet.run({"name": "Ada"})) == "hi Ada"


def test_bare_command_decorator_name_and_help_override():
    @command(name="renamed", help="custom help")
    @argument("x")
    def cmd(x):
        return x

    assert cmd.name == "renamed"
    assert cmd.help == "custom help"
    assert {p.name for p in cmd.params} == {"x"}


# --- generic-typed params must not crash type conversion --------------------


def test_convert_scalar_handles_parameterized_generic():
    """A param whose `type` is a parameterized generic (e.g. list[str]) must
    not raise TypeError from `isinstance(value, type)`."""
    param = Param("tags", ParamType.OPTION, type=list[str])

    def f(tags):
        return tags

    cmd = Command(f)
    cmd.add_param(param)
    # Should not raise; the scalar is returned unchanged for an unknown type.
    assert cmd._convert_scalar("abc", param) == "abc"


def test_command_with_generic_annotated_param_runs():
    """A command whose param type is inferred as a generic must still run."""

    @command()
    @option("--tags", multiple=True, default=None)
    def cmd(tags: list[str]):
        return tags

    result = asyncio.run(cmd.run({"tags": ["a", "b"]}))
    assert result == ["a", "b"]


# --- glob_files recursive expansion -----------------------------------------


def test_glob_files_recursive_descends_into_subdirs(tmp_path):
    """glob_files(recursive=True) with `*.py` must match nested files too."""
    (tmp_path / "top.py").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.py").touch()
    (tmp_path / "ignore.txt").touch()

    found = glob_files("*.py", base_dir=str(tmp_path), recursive=True)
    names = sorted(p.rsplit("/", 1)[-1] for p in found)
    assert names == ["nested.py", "top.py"]


def test_glob_files_non_recursive_stays_shallow(tmp_path):
    """recursive=False must not descend into subdirectories."""
    (tmp_path / "top.py").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.py").touch()

    found = glob_files("*.py", base_dir=str(tmp_path), recursive=False)
    names = sorted(p.rsplit("/", 1)[-1] for p in found)
    assert names == ["top.py"]


def test_glob_files_recursive_with_explicit_globstar(tmp_path):
    """A pattern already containing ** is passed through unchanged."""
    (tmp_path / "top.py").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.py").touch()

    found = glob_files("**/*.py", base_dir=str(tmp_path), recursive=True)
    names = sorted(p.rsplit("/", 1)[-1] for p in found)
    assert names == ["nested.py", "top.py"]
