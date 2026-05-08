declare global {
  interface Window {
    loadPyodide?: (opts: { indexURL: string }) => Promise<PyodideAPI>;
  }
}

export interface PyodideAPI {
  runPythonAsync: (code: string) => Promise<unknown>;
  loadPackage: (name: string | string[]) => Promise<void>;
  pyimport: (mod: string) => unknown;
  globals: {
    get: (k: string) => unknown;
    set: (k: string, v: unknown) => void;
  };
  setStdout: (opts: { batched: (s: string) => void }) => void;
  setStderr: (opts: { batched: (s: string) => void }) => void;
}

const PYODIDE_VERSION = "0.27.7";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full`;

let pyodidePromise: Promise<PyodideAPI> | null = null;

async function injectScript(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = url;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load ${url}`));
    document.head.appendChild(s);
  });
}

export async function getPyodide(): Promise<PyodideAPI> {
  if (pyodidePromise) return pyodidePromise;

  pyodidePromise = (async () => {
    if (!window.loadPyodide) {
      await injectScript(`${PYODIDE_CDN}/pyodide.js`);
    }
    if (!window.loadPyodide) throw new Error("loadPyodide not exposed by Pyodide bootstrap");
    const pyodide = await window.loadPyodide({ indexURL: `${PYODIDE_CDN}/` });
    await pyodide.loadPackage(["micropip"]);

    // Locate the wheel relative to the site base path.
    const base = import.meta.env.BASE_URL;
    const baseClean = base.endsWith("/") ? base : base + "/";
    const wheelDir = `${window.location.origin}${baseClean}wheels/`;
    // Discover the wheel filename (we ship exactly one).
    const wheelListUrl = `${baseClean}wheels-list.json`;
    let wheelFilename: string;
    try {
      const r = await fetch(wheelListUrl);
      if (!r.ok) throw new Error("no wheel list");
      const list = (await r.json()) as { wheels: string[] };
      const first = list.wheels[0];
      if (!first) throw new Error("no wheels in list");
      wheelFilename = first;
    } catch {
      // Fallback: try a known-pattern fetch.
      const candidate = "clir-0.1.0-py3-none-any.whl";
      const head = await fetch(`${wheelDir}${candidate}`, { method: "HEAD" });
      if (!head.ok) throw new Error("clir wheel not found in /wheels/");
      wheelFilename = candidate;
    }

    await pyodide.runPythonAsync(`
import micropip
await micropip.install("${wheelDir}${wheelFilename}")
`);

    return pyodide;
  })();

  return pyodidePromise;
}

export interface RunResult {
  stdout: string;
  stderr: string;
  error: string | null;
}

export async function runPython(code: string): Promise<RunResult> {
  const pyodide = await getPyodide();
  let stdout = "";
  let stderr = "";

  pyodide.setStdout({ batched: (s) => { stdout += s; } });
  pyodide.setStderr({ batched: (s) => { stderr += s; } });

  // Wrap user code so rich emits truecolor ANSI even though it's not on a TTY.
  // Patch the clir module's consoles BEFORE user code runs.
  const wrapped = `
import sys
from rich.console import Console
from rich.theme import Theme
import clir.output.style as _style

# Build a Theme from the active theme's truecolor palette so [success]/[error]/etc.
# resolve to actual styles.
_theme_colors = _style._THEME_COLORS.get(_style._current_theme_name, _style._THEME_COLORS["default"])
_palette = _theme_colors.get("truecolor", _theme_colors.get("basic", {}))
_theme = Theme(_palette) if _palette else None

_style.console = Console(file=sys.stdout, force_terminal=True, color_system="truecolor", width=100, theme=_theme)
_style._stderr_console = Console(file=sys.stderr, force_terminal=True, color_system="truecolor", width=100, theme=_theme)

${code}
`;

  let error: string | null = null;
  try {
    await pyodide.runPythonAsync(wrapped);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }
  return { stdout, stderr, error };
}
