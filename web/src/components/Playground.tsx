import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import { ansiToHtml } from "../lib/ansi";
import { runPython } from "../lib/pyodide";
import loader from "@monaco-editor/loader";

const DEFAULT_CODE = `from clir.output import success, info

success("Hello from the playground!")
info("Click Run to execute this Python in your browser.")
`;

interface ExampleEntry {
  slug: string;
  code: string;
}

interface Props {
  initialCode?: string | null;
  examples?: ExampleEntry[];
}

export default function Playground({ initialCode, examples }: Props) {
  const [code, setCode] = useState<string>(initialCode ?? DEFAULT_CODE);
  const [outputHtml, setOutputHtml] = useState<string>("");
  const [status, setStatus] = useState<string>("Ready");
  const [running, setRunning] = useState<boolean>(false);
  const editorContainer = useRef<HTMLDivElement>(null);
  const editorRef = useRef<unknown>(null);
  const runHandlerRef = useRef<() => Promise<void>>();

  // Resolve initial code from URL on mount. Priority:
  //   1. ?example=<slug>   → look up in `examples` prop
  //   2. #code=<base64>    → decode shared link
  //   3. localStorage      → restore last session
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const slug = params.get("example");
    if (slug && examples) {
      const found = examples.find((e) => e.slug === slug);
      if (found) {
        setCode(found.code);
        return;
      }
    }

    const hash = window.location.hash;
    const m = /#code=([^&]+)/.exec(hash);
    if (m) {
      try {
        const decoded = atob(decodeURIComponent(m[1]!));
        setCode(decoded);
        return;
      } catch {
        // fallthrough
      }
    }
    const stored = window.localStorage.getItem("clir-playground-code");
    if (stored) setCode(stored);
  }, []);

  // Persist on change.
  useEffect(() => {
    window.localStorage.setItem("clir-playground-code", code);
  }, [code]);

  const runHandler = useCallback(async (): Promise<void> => {
    if (running) return;
    setRunning(true);
    setStatus("Booting Python (first run takes a few seconds)...");
    try {
      const currentCode =
        (editorRef.current as { getValue: () => string } | null)?.getValue() ??
        code;
      const result = await runPython(currentCode);
      setStatus(result.error ? "Run completed with errors" : "Run complete");
      const stdout = ansiToHtml(result.stdout);
      const stderr = result.stderr
        ? `<div class="stderr-mark">${ansiToHtml(result.stderr)}</div>`
        : "";
      const errorBlock = result.error
        ? `<pre class="ansi" style="color:#ef4444">${result.error
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")}</pre>`
        : "";
      setOutputHtml(stdout + stderr + errorBlock);
    } catch (e) {
      setStatus(`Failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setRunning(false);
    }
  }, [running, code]);

  // Keep runHandlerRef pointing at the latest runHandler so the Monaco
  // keybinding (registered once at editor mount) always invokes the
  // current closure rather than a stale snapshot.
  useEffect(() => {
    runHandlerRef.current = runHandler;
  }, [runHandler]);

  // Mount Monaco.
  useEffect(() => {
    if (!editorContainer.current) return;
    let disposed = false;
    loader.init().then((monaco) => {
      if (disposed) return;
      const editor = monaco.editor.create(editorContainer.current!, {
        value: code,
        language: "python",
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
        fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace",
      });
      editor.onDidChangeModelContent(() => {
        setCode(editor.getValue());
      });
      editorRef.current = editor;

      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
        runHandlerRef.current?.();
      });
    });
    return () => {
      disposed = true;
    };
  }, []);

  // Sync external code changes (e.g., from URL hash) into Monaco.
  useEffect(() => {
    const e = editorRef.current as
      | { getValue: () => string; setValue: (v: string) => void }
      | null;
    if (e && e.getValue() !== code) e.setValue(code);
  }, [code]);

  return (
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[calc(100vh-200px)]">
      <div class="flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm opacity-70">Editor (Cmd/Ctrl+Enter to run)</span>
          <button
            onClick={runHandler}
            disabled={running}
            class="px-4 py-1.5 rounded bg-accent text-ink-900 font-medium disabled:opacity-50 hover:bg-accent-dark transition"
          >
            {running ? "Running..." : "▶ Run"}
          </button>
        </div>
        <div
          ref={editorContainer}
          class="flex-1 border border-ink-50/10 rounded overflow-hidden"
        />
      </div>
      <div class="flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm opacity-70">Output</span>
          <span class="text-xs opacity-50">{status}</span>
        </div>
        <div
          class="flex-1 border border-ink-50/10 rounded overflow-auto bg-black p-2"
          dangerouslySetInnerHTML={{
            __html:
              outputHtml ||
              `<div class="text-ink-50/30 text-sm p-2">Click Run to execute.</div>`,
          }}
        />
      </div>
    </div>
  );
}
