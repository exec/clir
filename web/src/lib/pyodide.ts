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
    // Load Pyodide-bundled packages that are clir's transitive deps but
    // aren't auto-installed by micropip when it processes the clir wheel.
    // `wcwidth` is required by prompt_toolkit; `pydantic` has Rust extensions
    // and is shipped with Pyodide rather than installed from PyPI.
    await pyodide.loadPackage(["micropip", "wcwidth", "pydantic"]);

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

    // Install clir alongside its pure-Python transitive deps. micropip's
    // dependency resolver sometimes misses deps declared deep in the chain
    // (e.g. rich → markdown-it-py → mdurl), so we list them explicitly.
    await pyodide.runPythonAsync(`
import micropip
await micropip.install([
    "markdown-it-py",
    "mdurl",
    "pygments",
    "${wheelDir}${wheelFilename}",
])
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

  // batched fires per-line and strips the trailing newline; re-add it so
  // successive print() calls don't concatenate into a single line.
  pyodide.setStdout({ batched: (s) => { stdout += s + "\n"; } });
  pyodide.setStderr({ batched: (s) => { stderr += s + "\n"; } });

  // Wrap user code so rich emits truecolor ANSI even though it's not on a TTY,
  // and so that subsequent set_theme() calls keep emitting ANSI too.
  const wrapped = `
from clir.output import force_terminal as _force_terminal
_force_terminal(True, "truecolor")

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
