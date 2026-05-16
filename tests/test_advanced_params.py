"""Tests for advanced parameter features: repeatable options, fixed-arity
(nargs) options, dest-aliasing, and pathlib.Path-typed parameters."""

import asyncio
import json
from pathlib import Path

import pytest

from clir import ClirApp, argument, option
from clir.core.params import Param, ParamType
from clir.testing import CliRunner


def _json(result):
    """Parse a --json invocation's stdout into a Python value."""
    return json.loads(result.output)


# --- repeatable / "append" options ----------------------------------------


@pytest.fixture
def repeat_app():
    app = ClirApp(name="t")

    @app.command()
    @option("--salvage", multiple=True, default=None, help="Salvage file")
    def assemble(salvage):
        return salvage

    return app


def test_multiple_absent_yields_default(repeat_app):
    """An absent repeatable option yields its default, not an empty list."""
    # default=None lets the caller distinguish "not passed" from "passed empty".
    received = asyncio.run(repeat_app.commands["assemble"].run({}))
    assert received is None


def test_multiple_passed_once(repeat_app):
    runner = CliRunner(repeat_app)
    result = runner.invoke(["--json", "assemble", "--salvage", "a.jsonl"])
    assert result.success
    assert _json(result) == ["a.jsonl"]


def test_multiple_passed_several_times(repeat_app):
    runner = CliRunner(repeat_app)
    result = runner.invoke(
        ["--json", "assemble", "--salvage", "a.jsonl", "--salvage", "b.jsonl"]
    )
    assert result.success
    assert _json(result) == ["a.jsonl", "b.jsonl"]


def test_multiple_with_int_type_converts_each_element():
    app = ClirApp(name="t")

    @app.command()
    @option("--n", multiple=True, type=int, default=None)
    def cmd(n):
        return n

    runner = CliRunner(app)
    result = runner.invoke(["--json", "cmd", "--n", "1", "--n", "2"])
    assert result.success
    assert _json(result) == [1, 2]


# --- fixed-arity (nargs) options -------------------------------------------


@pytest.fixture
def nargs_app():
    app = ClirApp(name="t")

    @app.command()
    @option("--compare", nargs=2, default=None, help="Two models to compare")
    def evaluate(compare):
        return compare

    return app


def test_nargs_absent_yields_default(nargs_app):
    received = asyncio.run(nargs_app.commands["evaluate"].run({}))
    assert received is None


def test_nargs_consumes_exactly_n_values(nargs_app):
    runner = CliRunner(nargs_app)
    result = runner.invoke(["--json", "evaluate", "--compare", "modelA", "modelB"])
    assert result.success
    assert _json(result) == ["modelA", "modelB"]


def test_nargs_too_few_values_fails(nargs_app):
    runner = CliRunner(nargs_app)
    result = runner.invoke(["evaluate", "--compare", "onlyone"])
    assert not result.success


def test_nargs_with_int_type_converts_each_element():
    app = ClirApp(name="t")

    @app.command()
    @option("--span", nargs=2, type=int, default=None)
    def cmd(span):
        return span

    runner = CliRunner(app)
    result = runner.invoke(["--json", "cmd", "--span", "10", "20"])
    assert result.success
    assert _json(result) == [10, 20]


def test_nargs_zero_rejected():
    """nargs must be >= 1."""
    with pytest.raises(ValueError):
        Param("x", ParamType.OPTION, nargs=0)


# --- dest-aliasing ----------------------------------------------------------


def test_dest_alias_option_binds_to_python_param():
    """A flag whose spelling is a Python keyword binds via dest."""
    app = ClirApp(name="t")

    @app.command()
    @option("--in", dest="in_path", help="Input file")
    def triage(in_path):
        return in_path

    runner = CliRunner(app)
    result = runner.invoke(["--json", "triage", "--in", "data.jsonl"])
    assert result.success
    assert _json(result) == "data.jsonl"


def test_dest_alias_argument_binds_to_python_param():
    app = ClirApp(name="t")

    @app.command()
    @argument("class", dest="class_name")
    def show(class_name):
        return class_name

    runner = CliRunner(app)
    result = runner.invoke(["--json", "show", "Widget"])
    assert result.success
    assert _json(result) == "Widget"


def test_dest_alias_appears_in_help_with_flag_spelling():
    """Help shows the CLI flag spelling, not the dest."""
    from tests.test_help import _capture_render

    app = ClirApp(name="t")

    @app.command()
    @option("--in", dest="in_path", help="Input file")
    def triage(in_path):
        pass

    out = _capture_render(app.commands["triage"], app_name="t")
    assert "--in" in out
    assert "in_path" not in out


def test_param_dest_defaults_to_name():
    p = Param("verbose", ParamType.OPTION)
    assert p.dest == "verbose"


# --- pathlib.Path-typed parameters -----------------------------------------


def test_path_type_accepted_and_converted():
    app = ClirApp(name="t")

    @app.command()
    @option("--prompts", type=Path, default=None)
    def evaluate(prompts):
        return prompts

    runner = CliRunner(app)
    result = runner.invoke(["evaluate", "--prompts", "/tmp/p.jsonl"])
    assert result.success

    # Verify the function actually receives a Path, not a str.
    received = asyncio.run(
        app.commands["evaluate"].run({"prompts": "/tmp/p.jsonl"})
    )
    assert isinstance(received, Path)
    assert received == Path("/tmp/p.jsonl")


def test_path_argument_type_accepted():
    """Path is a valid type for arguments too."""
    p = Param("file", ParamType.ARGUMENT, type=Path)
    assert p.type is Path


# --- required-option error message -----------------------------------------


def test_missing_required_option_names_the_flag():
    """A missing required option reports --flag, not the bare dest."""
    app = ClirApp(name="t")

    @app.command()
    @option("--project-dir", required=True)
    def deploy(project_dir):
        return project_dir

    runner = CliRunner(app)
    result = runner.invoke(["deploy"])
    assert not result.success
    assert "--project-dir" in result.error


def test_required_option_alongside_optional_options():
    app = ClirApp(name="t")

    @app.command()
    @option("--project", required=True)
    @option("--extra", default="x")
    def deploy(project, extra):
        return f"{project}:{extra}"

    runner = CliRunner(app)
    result = runner.invoke(["--json", "deploy", "--project", "p"])
    assert result.success
    assert _json(result) == "p:x"


# --- guardrails: argument-only restrictions --------------------------------


def test_multiple_rejected_on_argument():
    with pytest.raises(ValueError):
        Param("x", ParamType.ARGUMENT, multiple=True)


def test_nargs_rejected_on_argument():
    with pytest.raises(ValueError):
        Param("x", ParamType.ARGUMENT, nargs=2)


# --- help rendering for value placeholders ---------------------------------


def test_help_shows_nargs_metavars():
    from tests.test_help import _capture_render

    app = ClirApp(name="t")

    @app.command()
    @option("--compare", nargs=2, default=None, help="Two models")
    def evaluate(compare):
        pass

    out = _capture_render(app.commands["evaluate"], app_name="t")
    assert "COMPARE COMPARE" in out


def test_help_shows_multiple_ellipsis():
    from tests.test_help import _capture_render

    app = ClirApp(name="t")

    @app.command()
    @option("--salvage", multiple=True, default=None, help="Salvage files")
    def assemble(salvage):
        pass

    out = _capture_render(app.commands["assemble"], app_name="t")
    assert "SALVAGE ..." in out
