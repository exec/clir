#!/usr/bin/env python3
"""
advanced_options — A clir example for advanced @option features.

Demonstrates:
  Repeatable:   @option(multiple=True)   — pass a flag many times -> list
  Fixed-arity:  @option(nargs=N)         — a flag that takes N values at once
  Dest-alias:   @option(dest="...")      — flag spelling != Python parameter
  Path type:    @option(type=Path)       — function receives a pathlib.Path

Usage:
    python advanced_options.py --version
    python advanced_options.py merge --salvage a.jsonl --salvage b.jsonl
    python advanced_options.py compare --models modelA modelB
    python advanced_options.py convert --in input.csv --out result.json
    python advanced_options.py merge --help
"""

from pathlib import Path

from clir import ClirApp, option
from clir.output import echo, info, success

app = ClirApp(
    name="advanced",
    description="Demo of repeatable, fixed-arity, and dest-aliased options.",
    version="1.0.0",
)


@app.command()
@option("--salvage", multiple=True, default=None, help="File to merge in (repeatable)")
@option("--out", type=Path, default=None, help="Where to write the merged result")
def merge(salvage, out):
    """Merge one or more salvage files.

    --salvage may be passed any number of times; the values arrive as a list.
    An absent --salvage is None (not []), so "not passed" is distinguishable.
    """
    files = salvage or []
    if not files:
        info("No --salvage files given; nothing to merge.")
        return
    success(f"Merging {len(files)} file(s): {', '.join(files)}")
    if out is not None:
        # `out` is a pathlib.Path — Path is a first-class @option type.
        echo(f"Writing result to {out} (suffix: {out.suffix})")


@app.command()
@option("--models", nargs=2, default=None, help="Exactly two models to compare")
def compare(models):
    """Compare exactly two models.

    nargs=2 makes --models consume two values at once: --models A B.
    Passing fewer than two raises a clear argparse error.
    """
    if models is None:
        info("Pass --models A B to compare two models.")
        return
    left, right = models
    success(f"Comparing {left!r} against {right!r}")


@app.command()
@option("--in", dest="in_path", help="Input file (flag --in -> param in_path)")
@option("--out", dest="out_path", type=Path, default=None, help="Output file")
def convert(in_path, out_path):
    """Convert a file.

    The flag is spelled --in, but `in` is a Python keyword, so it cannot be a
    parameter name. dest="in_path" binds the flag to the in_path parameter.
    """
    if in_path is None:
        info("Pass --in <file> to convert.")
        return
    target = out_path or Path(in_path).with_suffix(".out")
    success(f"Converting {in_path} -> {target}")


if __name__ == "__main__":
    app.run()
