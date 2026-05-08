#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.resolve(__dirname, "..");
const EXAMPLES_DIR = path.join(WEB_DIR, "src", "examples");
const REPO_ROOT = path.resolve(WEB_DIR, "..");

// Locate Python interpreter from the project venv.
const VENV_PY = path.join(REPO_ROOT, ".venv", "bin", "python");
if (!fs.existsSync(VENV_PY)) {
  console.error(`Error: Python venv not found at ${VENV_PY}`);
  console.error("Create with: python3 -m venv .venv && .venv/bin/pip install -e .[dev]");
  process.exit(1);
}

// Load the converter via tsx-to-stdout. tsx is a dev dep of web/.
const tsxBin = path.join(WEB_DIR, "node_modules", ".bin", "tsx");
if (!fs.existsSync(tsxBin)) {
  console.log("Installing tsx (one-time)...");
  spawnSync("npm", ["install", "--save-dev", "tsx"], { cwd: WEB_DIR, stdio: "inherit" });
}

function ansiToHtml(ansi) {
  const result = spawnSync(
    tsxBin,
    [
      "-e",
      `
      import { ansiToHtml } from "${path.join(WEB_DIR, "src/lib/ansi.ts").replace(/\\\\/g, "/")}";
      let chunks = [];
      process.stdin.on("data", (c) => chunks.push(c));
      process.stdin.on("end", () => {
        const input = Buffer.concat(chunks).toString("utf-8");
        process.stdout.write(ansiToHtml(input));
      });
      `,
    ],
    { input: ansi, encoding: "utf-8" },
  );
  if (result.status !== 0) {
    throw new Error(`ansiToHtml failed: ${result.stderr}`);
  }
  return result.stdout;
}

const PRERENDER_PY = `
import io
import sys
import contextlib
from rich.console import Console
from rich.theme import Theme

# Force rich to emit truecolor ANSI even though we're not on a TTY.
import clir.output.style as _style

# Build a theme matching the active clir theme so [success]/[info]/[warning]/[error]
# tags resolve to colored styles when piped through rich.
_theme_colors = _style._THEME_COLORS.get(_style._current_theme_name, _style._THEME_COLORS["default"])
_colors = _theme_colors.get("truecolor", _theme_colors["basic"])
_custom_theme = Theme(_colors)

stdout_buf = io.StringIO()
stderr_buf = io.StringIO()

with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
    # Re-patch consoles to point to the redirected streams (post-redirect).
    _style.console = Console(
        file=sys.stdout, force_terminal=True, color_system="truecolor",
        width=100, theme=_custom_theme,
    )
    _style._stderr_console = Console(
        file=sys.stderr, force_terminal=True, color_system="truecolor",
        width=100, theme=_custom_theme,
    )
    code_path = sys.argv[1]
    code_str = open(code_path).read()
    code_obj = compile(code_str, code_path, "exec")
    runtime_globals = {"__name__": "__main__"}
    exec(code_obj, runtime_globals)

# Print stdout, then a marker, then stderr — so the JS side can split.
sys.__stdout__.write(stdout_buf.getvalue())
sys.__stdout__.write("\\x1e")  # ASCII RS as a separator (rich won't emit this)
sys.__stdout__.write(stderr_buf.getvalue())
`;

const slugs = fs
  .readdirSync(EXAMPLES_DIR)
  .filter((name) => fs.statSync(path.join(EXAMPLES_DIR, name)).isDirectory());

let failed = 0;
for (const slug of slugs) {
  const dir = path.join(EXAMPLES_DIR, slug);
  const codePath = path.join(dir, "code.py");
  const outPath = path.join(dir, "output.html");
  if (!fs.existsSync(codePath)) continue;

  try {
    const result = spawnSync(VENV_PY, ["-c", PRERENDER_PY, codePath], {
      encoding: "utf-8",
      maxBuffer: 8 * 1024 * 1024,
    });
    if (result.status !== 0) {
      console.error(`✗ ${slug}: Python failed`);
      console.error(result.stderr);
      failed += 1;
      continue;
    }
    const [stdoutAnsi, stderrAnsi] = result.stdout.split("\x1e");
    const stdoutHtml = ansiToHtml(stdoutAnsi || "");
    const stderrHtml = ansiToHtml(stderrAnsi || "");
    const combined = `<div class="example-output">${stdoutHtml}${stderrAnsi ? `<div class="stderr-mark">${stderrHtml}</div>` : ""}</div>`;
    fs.writeFileSync(outPath, combined, "utf-8");
    console.log(`✓ ${slug}`);
  } catch (err) {
    console.error(`✗ ${slug}: ${err.message}`);
    failed += 1;
  }
}

if (failed > 0) {
  console.error(`Pre-render: ${failed} example(s) failed.`);
  process.exit(1);
}
console.log(`Pre-render: ${slugs.length} example(s) OK.`);
