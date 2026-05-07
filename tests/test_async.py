"""Tests for ClirApp.run_async — async-callable entry point."""

import asyncio
import pytest

from clir import ClirApp
from clir.errors import ClirError


@pytest.mark.asyncio
async def test_run_async_executes_command():
    app = ClirApp(name="myapp")
    out = []

    @app.command()
    def hello():
        out.append("ran")

    await app.run_async(["hello"])
    assert out == ["ran"]


@pytest.mark.asyncio
async def test_run_async_returns_none_for_help_short_circuit():
    app = ClirApp(name="myapp")

    @app.command()
    def hello():
        pass

    # Top-level --help renders help and returns (no sys.exit).
    result = await app.run_async(["--help"])
    assert result is None


@pytest.mark.asyncio
async def test_run_async_default_command():
    app = ClirApp(name="myapp")
    seen = []

    @app.command()
    def main():
        seen.append("default")

    app.default(app.commands["main"])
    await app.run_async([])
    assert seen == ["default"]


@pytest.mark.asyncio
async def test_run_async_executes_group_command():
    app = ClirApp(name="myapp")
    out = []

    @app.group()
    def db():
        """DB."""
        pass

    @db.command()
    def migrate():
        out.append("migrated")

    await app.run_async(["db", "migrate"])
    assert out == ["migrated"]


@pytest.mark.asyncio
async def test_run_async_executes_nested_group_command():
    app = ClirApp(name="myapp")
    out = []

    @app.group()
    def outer():
        pass

    @outer.group()
    def inner():
        pass

    @inner.command()
    def deep():
        out.append("deep")

    await app.run_async(["outer", "inner", "deep"])
    assert out == ["deep"]


@pytest.mark.asyncio
async def test_run_async_propagates_command_error():
    app = ClirApp(name="myapp")

    @app.command()
    def boom():
        raise ClirError("user-facing", exit_code=42)

    with pytest.raises(SystemExit) as exc_info:
        await app.run_async(["boom"])
    assert exc_info.value.code == 42


def test_sync_run_still_works():
    app = ClirApp(name="myapp")
    seen = []

    @app.command()
    def hello():
        seen.append("ran")

    app.run(["hello"])
    assert seen == ["ran"]


def test_sync_run_still_works_for_groups():
    app = ClirApp(name="myapp")
    out = []

    @app.group()
    def db():
        pass

    @db.command()
    def migrate():
        out.append("migrated")

    app.run(["db", "migrate"])
    assert out == ["migrated"]
