#!/usr/bin/env bash
set -euo pipefail

# Builds the clir wheel from the repo root and copies it to web/public/wheels/.
# Idempotent: removes existing wheels first.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$WEB_DIR")"

cd "$REPO_ROOT"

if [[ ! -d ".venv" ]]; then
  echo "Error: .venv not found at $REPO_ROOT/.venv. Create it with python3 -m venv .venv && pip install -e .[dev] build"
  exit 1
fi

source .venv/bin/activate
python -m pip install --upgrade build >/dev/null

# Clean and build
rm -rf dist/
python -m build --wheel >/dev/null

WHEEL=$(ls dist/clir-*.whl | head -1)
if [[ -z "$WHEEL" ]]; then
  echo "Error: build did not produce a wheel"
  exit 1
fi

WHEEL_DIR="$WEB_DIR/public/wheels"
mkdir -p "$WHEEL_DIR"
rm -f "$WHEEL_DIR"/clir-*.whl
cp "$WHEEL" "$WHEEL_DIR/"
echo "Wheel: $WHEEL_DIR/$(basename "$WHEEL")"
