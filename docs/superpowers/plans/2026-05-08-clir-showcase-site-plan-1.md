# Clir Showcase Site Plan 1: Foundation + Docs + Minimal Playground + Deploy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a live GitHub Pages site at `https://exec.github.io/clir` that renders all 19 clir feature examples with character-perfect output (build-time pre-rendered) plus a minimal in-browser playground (Monaco editor + Pyodide + clir wheel + Run button).

**Architecture:** Astro static site under `web/`. Build pipeline: build clir wheel → run each example through real CPython subprocess → capture ANSI → convert to HTML at build → embed in pages. Playground lazy-loads Pyodide and the same wheel; reuses the same ANSI→HTML converter. Site is fully static; deploys via GitHub Actions to `gh-pages`.

**Tech Stack:** Astro 4.x, Tailwind 3.x, TypeScript, Vitest (unit tests), Pyodide 0.27, Monaco Editor, Python 3.12 (build-time CPython for pre-render).

**Spec:** `docs/superpowers/specs/2026-05-08-clir-showcase-site-design.md`

**Out of scope for this plan (Plan 2 covers them):** Theme switcher across docs, `/themes` gallery, prompt bridging in playground, hero animation on landing, `--debug` traceback walkthrough, async-command demos in playground, visual regression CI, share-URL hash encoding.

**Plan 1 ships:** `/`, `/docs` (all 19 examples pre-rendered in default theme), `/playground` (Monaco + Run + output capture, no prompts/themes), GitHub Actions deploy.

---

## File structure

| Action  | Path                                            | Responsibility                                           |
|---------|-------------------------------------------------|----------------------------------------------------------|
| Create  | `web/package.json`                              | Astro + Tailwind + Monaco + Pyodide deps.                |
| Create  | `web/astro.config.mjs`                          | Astro config (tailwind, base path).                      |
| Create  | `web/tailwind.config.mjs`                       | Theme tokens (font, colors).                             |
| Create  | `web/tsconfig.json`                             | TS config extending Astro's strictest.                   |
| Create  | `web/.gitignore`                                | Excludes `node_modules/`, `dist/`, `.astro/`.            |
| Create  | `web/src/styles/global.css`                     | Tailwind base + custom CSS.                              |
| Create  | `web/src/lib/ansi.ts`                           | ANSI→HTML converter (shared by build + playground).      |
| Create  | `web/src/lib/ansi.test.ts`                      | Vitest unit tests for the converter.                     |
| Create  | `web/src/lib/pyodide.ts`                        | Pyodide bootstrap + clir wheel install.                  |
| Create  | `web/src/lib/examples.ts`                       | Loads example metadata + pre-rendered output at build.   |
| Create  | `web/src/components/Layout.astro`               | Base page layout (header, footer, head).                 |
| Create  | `web/src/components/CodeBlock.astro`            | Tabbed code/output presentation with copy button.        |
| Create  | `web/src/components/Sidebar.astro`              | Sidebar TOC for `/docs`.                                 |
| Create  | `web/src/components/Playground.tsx` (or .astro) | Monaco editor + run button + output pane (Preact island).|
| Create  | `web/src/pages/index.astro`                     | Landing page.                                            |
| Create  | `web/src/pages/docs.astro`                      | Long-scroll docs with all 19 examples.                   |
| Create  | `web/src/pages/playground.astro`                | Hosts the Playground island.                             |
| Create  | `web/src/examples/<slug>/code.py`               | Source for each example. (×19)                           |
| Create  | `web/src/examples/<slug>/meta.json`             | Title, section, description for each example. (×19)      |
| Create  | `web/scripts/build-wheel.sh`                    | Builds clir wheel into `web/public/wheels/`.             |
| Create  | `web/scripts/prerender-docs.mjs`                | Runs each example, captures ANSI, writes output.html.    |
| Create  | `web/public/CNAME`                              | (Empty placeholder; user fills in if custom domain.)     |
| Create  | `.github/workflows/deploy-site.yml`             | Build + deploy to gh-pages.                              |
| Modify  | `.gitignore` (root)                             | Add `web/dist/`, `web/node_modules/`, `web/.astro/`.     |

Pyodide self-host comes in Plan 2 (Plan 1 loads it from the official CDN; Plan 2 self-hosts to remove third-party dependency).

---

## Task 0: Pre-flight

**Files:** none

- [ ] **Step 1: Verify state**

```bash
cd /Users/dylan/Developer/clir
git log --oneline | head -3
test ! -d web && echo "web/ does not exist (correct)"
node --version  # expect v20+
npm --version
```

Expected: HEAD is `4902293 feat(app): split run into sync wrapper + async run_async, share event loop`. `web/` does not exist. Node 20+ installed.

- [ ] **Step 2: Capture base SHA**

```bash
git rev-parse HEAD
```

Record this as `BASE_SHA` for the per-task subagent reviews.

---

## Task 1: Bootstrap Astro project skeleton

**Files:**
- Create: `web/package.json`, `web/astro.config.mjs`, `web/tsconfig.json`, `web/.gitignore`, `web/src/pages/index.astro`, `web/src/styles/global.css`, `web/tailwind.config.mjs`
- Modify: `.gitignore` (root)

This task creates a runnable Astro project with Tailwind and TypeScript, displaying a placeholder landing page. Subsequent tasks fill in real content.

- [ ] **Step 1: Create `web/package.json`**

```json
{
  "name": "clir-site",
  "private": true,
  "type": "module",
  "version": "0.0.1",
  "scripts": {
    "dev": "astro dev",
    "build": "node scripts/prerender-docs.mjs && astro build",
    "preview": "astro preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@astrojs/preact": "^4.0.0",
    "@astrojs/tailwind": "^5.1.0",
    "astro": "^4.16.0",
    "preact": "^10.24.0",
    "tailwindcss": "^3.4.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "typescript": "^5.6.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create `web/astro.config.mjs`**

```js
import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";
import preact from "@astrojs/preact";

export default defineConfig({
  site: "https://exec.github.io",
  base: "/clir",
  integrations: [tailwind(), preact()],
  output: "static",
  build: {
    assets: "assets",
  },
});
```

- [ ] **Step 3: Create `web/tsconfig.json`**

```json
{
  "extends": "astro/tsconfigs/strictest",
  "compilerOptions": {
    "jsx": "preserve",
    "jsxImportSource": "preact"
  },
  "include": ["src/**/*", "scripts/**/*"]
}
```

- [ ] **Step 4: Create `web/.gitignore`**

```
node_modules/
dist/
.astro/
*.log
.DS_Store
```

- [ ] **Step 5: Create `web/tailwind.config.mjs`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{astro,html,js,jsx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "Menlo", "monospace"],
      },
      colors: {
        ink: { 50: "#fafaf9", 900: "#0a0a0b" },
        accent: { DEFAULT: "#22d3ee", dark: "#0891b2" },
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 6: Create `web/src/styles/global.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html {
  scroll-behavior: smooth;
}

body {
  @apply bg-ink-50 text-ink-900 dark:bg-ink-900 dark:text-ink-50 font-sans;
}

pre, code {
  @apply font-mono;
}
```

- [ ] **Step 7: Create placeholder `web/src/pages/index.astro`**

```astro
---
import "../styles/global.css";
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Clir — modern CLI toolkit for Python</title>
  </head>
  <body class="min-h-screen flex items-center justify-center">
    <main class="text-center max-w-xl">
      <h1 class="text-5xl font-bold tracking-tight">clir</h1>
      <p class="mt-4 text-lg text-ink-900/70 dark:text-ink-50/70">
        A modern CLI toolkit for building beautiful terminal applications in Python.
      </p>
      <p class="mt-8 text-sm opacity-50">Site under construction.</p>
    </main>
  </body>
</html>
```

- [ ] **Step 8: Append to root `.gitignore`**

Append these lines to `/Users/dylan/Developer/clir/.gitignore`:

```
web/node_modules/
web/dist/
web/.astro/
```

- [ ] **Step 9: Install deps and verify dev server starts**

```bash
cd /Users/dylan/Developer/clir/web
npm install
npm run dev -- --host 127.0.0.1 --port 4321 &
sleep 3
curl -sf http://127.0.0.1:4321/clir/ | head -20
kill %1
```

Expected: HTML containing `<h1 class="text-5xl font-bold tracking-tight">clir</h1>`. If `npm install` fails, do NOT proceed — investigate (likely network issue or corrupt registry cache).

- [ ] **Step 10: Verify production build succeeds**

```bash
cd /Users/dylan/Developer/clir/web
npm run build
test -f dist/index.html && echo "build OK"
```

The `npm run build` will fail at the `prerender-docs.mjs` step in Step 1 because that script doesn't exist yet. **This is expected.** Edit `package.json`'s `build` script to temporarily remove the prerender step:

```json
"build": "astro build",
```

Run `npm run build` — should succeed. Restore the original `build` script value (`node scripts/prerender-docs.mjs && astro build`) before committing. The script will be created in Task 5; the build will succeed end-to-end after that.

- [ ] **Step 11: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/ .gitignore
git commit -m "feat(web): bootstrap Astro project with Tailwind and Preact"
```

---

## Task 2: ANSI→HTML converter with unit tests

**Files:**
- Create: `web/src/lib/ansi.ts`
- Create: `web/src/lib/ansi.test.ts`

The single most-load-bearing module on the site. Used by both build-time pre-render (Task 5) and runtime playground (Task 11). TDD this carefully.

- [ ] **Step 1: Write failing tests**

Create `web/src/lib/ansi.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ansiToHtml } from "./ansi";

describe("ansiToHtml", () => {
  it("returns plain text wrapped in pre when no codes", () => {
    expect(ansiToHtml("hello")).toBe(`<pre class="ansi">hello</pre>`);
  });

  it("escapes html special characters", () => {
    expect(ansiToHtml("<script>&\"'")).toContain("&lt;script&gt;&amp;&quot;&#39;");
  });

  it("renders bold via SGR 1", () => {
    const html = ansiToHtml("\x1b[1mbold\x1b[0m");
    expect(html).toContain('<span class="ansi-bold">bold</span>');
  });

  it("renders 4-bit foreground colors", () => {
    const html = ansiToHtml("\x1b[31mred\x1b[0m");
    expect(html).toContain('style="color:#cd3131"');
    expect(html).toContain(">red<");
  });

  it("renders 8-bit foreground colors", () => {
    const html = ansiToHtml("\x1b[38;5;208morange\x1b[0m");
    expect(html).toMatch(/style="color:#[0-9a-f]{6}"/);
    expect(html).toContain(">orange<");
  });

  it("renders truecolor foreground", () => {
    const html = ansiToHtml("\x1b[38;2;100;200;50mlime\x1b[0m");
    expect(html).toContain('style="color:#64c832"');
  });

  it("renders truecolor background", () => {
    const html = ansiToHtml("\x1b[48;2;0;0;255mblue\x1b[0m");
    expect(html).toContain('background:#0000ff');
  });

  it("composes bold + color in one span", () => {
    const html = ansiToHtml("\x1b[1;31mboldred\x1b[0m");
    expect(html).toMatch(/<span class="ansi-bold"[^>]*style="color:#cd3131"[^>]*>boldred<\/span>/);
  });

  it("resets at SGR 0", () => {
    const html = ansiToHtml("\x1b[31mred\x1b[0mplain");
    expect(html).toContain(">red<");
    expect(html).toContain(">plain<");
    // 'plain' should not be in a styled span
    expect(html).toMatch(/<\/span>plain/);
  });

  it("preserves unicode box-drawing characters", () => {
    expect(ansiToHtml("│  └─ leaf")).toContain("│  └─ leaf");
  });

  it("preserves whitespace and newlines", () => {
    expect(ansiToHtml("a\nb\n  c")).toContain("a\nb\n  c");
  });

  it("ignores cursor-control sequences (silently consumes)", () => {
    expect(ansiToHtml("\x1b[2K\x1b[1Aoverwritten")).not.toContain("\x1b");
  });

  it("handles dim, italic, underline modifiers", () => {
    expect(ansiToHtml("\x1b[2mdim\x1b[0m")).toContain("ansi-dim");
    expect(ansiToHtml("\x1b[3mit\x1b[0m")).toContain("ansi-italic");
    expect(ansiToHtml("\x1b[4mund\x1b[0m")).toContain("ansi-underline");
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd /Users/dylan/Developer/clir/web
npm run test
```

Expected: FAIL — `ansi.ts` does not exist.

- [ ] **Step 3: Implement `web/src/lib/ansi.ts`**

```ts
const FG_4BIT: Record<number, string> = {
  30: "#000000", 31: "#cd3131", 32: "#0dbc79", 33: "#e5e510",
  34: "#2472c8", 35: "#bc3fbc", 36: "#11a8cd", 37: "#e5e5e5",
  90: "#666666", 91: "#f14c4c", 92: "#23d18b", 93: "#f5f543",
  94: "#3b8eea", 95: "#d670d6", 96: "#29b8db", 97: "#ffffff",
};

const BG_4BIT: Record<number, string> = Object.fromEntries(
  Object.entries(FG_4BIT).map(([k, v]) => [String(Number(k) + 10), v]),
);

// 256-color palette: 0–15 = 4-bit; 16–231 = 6×6×6 cube; 232–255 = grayscale.
function color256(n: number): string {
  if (n < 16) {
    const map = [30, 31, 32, 33, 34, 35, 36, 37, 90, 91, 92, 93, 94, 95, 96, 97];
    return FG_4BIT[map[n]];
  }
  if (n < 232) {
    const i = n - 16;
    const r = Math.floor(i / 36) % 6;
    const g = Math.floor(i / 6) % 6;
    const b = i % 6;
    const v = (x: number) => (x === 0 ? 0 : 55 + x * 40);
    return rgb(v(r), v(g), v(b));
  }
  const v = 8 + (n - 232) * 10;
  return rgb(v, v, v);
}

function rgb(r: number, g: number, b: number): string {
  const h = (x: number) => x.toString(16).padStart(2, "0");
  return `#${h(r)}${h(g)}${h(b)}`;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

interface State {
  bold: boolean;
  dim: boolean;
  italic: boolean;
  underline: boolean;
  fg: string | null;
  bg: string | null;
}

const RESET: State = {
  bold: false, dim: false, italic: false, underline: false, fg: null, bg: null,
};

function spanOpen(state: State): string {
  const classes: string[] = [];
  const styles: string[] = [];
  if (state.bold) classes.push("ansi-bold");
  if (state.dim) classes.push("ansi-dim");
  if (state.italic) classes.push("ansi-italic");
  if (state.underline) classes.push("ansi-underline");
  if (state.fg) styles.push(`color:${state.fg}`);
  if (state.bg) styles.push(`background:${state.bg}`);

  const noStyle = classes.length === 0 && styles.length === 0;
  if (noStyle) return "";
  const cls = classes.length ? ` class="${classes.join(" ")}"` : "";
  const sty = styles.length ? ` style="${styles.join(";")}"` : "";
  return `<span${cls}${sty}>`;
}

function applyParams(state: State, params: number[]): State {
  const next = { ...state };
  let i = 0;
  while (i < params.length) {
    const p = params[i];
    if (p === 0) {
      Object.assign(next, RESET);
      i += 1;
      continue;
    }
    if (p === 1) { next.bold = true; i += 1; continue; }
    if (p === 2) { next.dim = true; i += 1; continue; }
    if (p === 3) { next.italic = true; i += 1; continue; }
    if (p === 4) { next.underline = true; i += 1; continue; }
    if (p === 22) { next.bold = false; next.dim = false; i += 1; continue; }
    if (p === 23) { next.italic = false; i += 1; continue; }
    if (p === 24) { next.underline = false; i += 1; continue; }
    if (p === 39) { next.fg = null; i += 1; continue; }
    if (p === 49) { next.bg = null; i += 1; continue; }
    if (p in FG_4BIT) { next.fg = FG_4BIT[p]; i += 1; continue; }
    if (p in BG_4BIT) { next.bg = BG_4BIT[p]; i += 1; continue; }
    if (p === 38 && params[i + 1] === 5) { next.fg = color256(params[i + 2]); i += 3; continue; }
    if (p === 48 && params[i + 1] === 5) { next.bg = color256(params[i + 2]); i += 3; continue; }
    if (p === 38 && params[i + 1] === 2) {
      next.fg = rgb(params[i + 2], params[i + 3], params[i + 4]);
      i += 5; continue;
    }
    if (p === 48 && params[i + 1] === 2) {
      next.bg = rgb(params[i + 2], params[i + 3], params[i + 4]);
      i += 5; continue;
    }
    // Unknown SGR — ignore and continue.
    i += 1;
  }
  return next;
}

export function ansiToHtml(input: string): string {
  // Strip cursor-control sequences (CSI ... letters other than 'm').
  // Pattern: ESC [ <params> <letter>; only 'm' is SGR.
  let state: State = { ...RESET };
  let out = "";
  let openSpan = "";
  let i = 0;

  const flushOpen = (): void => {
    if (openSpan) {
      out += "</span>";
      openSpan = "";
    }
    const next = spanOpen(state);
    if (next) {
      out += next;
      openSpan = next;
    }
  };

  while (i < input.length) {
    const ch = input[i];
    if (ch !== "\x1b") {
      out += escapeHtml(ch);
      i += 1;
      continue;
    }
    // ESC sequence
    if (input[i + 1] !== "[") {
      // Unknown ESC — skip ESC alone
      i += 1;
      continue;
    }
    // Read parameter bytes (digits, ;) until final byte (letter)
    let j = i + 2;
    while (j < input.length && !/[A-Za-z]/.test(input[j])) j += 1;
    if (j >= input.length) break;
    const final = input[j];
    const paramStr = input.slice(i + 2, j);
    if (final === "m") {
      const params = paramStr === "" ? [0] : paramStr.split(";").map((s) => Number(s) || 0);
      state = applyParams(state, params);
      flushOpen();
    }
    // For any other final byte (cursor moves, line clear, etc.) — silently consume.
    i = j + 1;
  }

  if (openSpan) out += "</span>";
  return `<pre class="ansi">${out}</pre>`;
}
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/dylan/Developer/clir/web
npm run test
```

Expected: all 13 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/src/lib/ansi.ts web/src/lib/ansi.test.ts
git commit -m "feat(web): add ANSI to HTML converter with unit tests"
```

---

## Task 3: Build clir wheel script

**Files:**
- Create: `web/scripts/build-wheel.sh`
- Create: `web/public/wheels/.gitkeep`

- [ ] **Step 1: Create `web/scripts/build-wheel.sh`**

```bash
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
```

- [ ] **Step 2: Make executable and run**

```bash
chmod +x /Users/dylan/Developer/clir/web/scripts/build-wheel.sh

# Need to add 'build' to dev deps first; install ad-hoc
cd /Users/dylan/Developer/clir
source .venv/bin/activate
pip install build

bash web/scripts/build-wheel.sh
ls web/public/wheels/
```

Expected: `clir-0.1.0-py3-none-any.whl` (or similar) in `web/public/wheels/`.

- [ ] **Step 3: Add `.gitkeep` to ensure directory tracked**

```bash
touch /Users/dylan/Developer/clir/web/public/wheels/.gitkeep
```

Add to `web/.gitignore` to prevent wheels from being committed (they're built in CI):

```
public/wheels/*.whl
!public/wheels/.gitkeep
```

- [ ] **Step 4: Smoke test the wheel**

```bash
cd /Users/dylan/Developer/clir
source .venv/bin/activate
python -m venv /tmp/clir-wheel-test
/tmp/clir-wheel-test/bin/pip install web/public/wheels/clir-*.whl
/tmp/clir-wheel-test/bin/python -c "from clir import ClirApp; print('OK', ClirApp(name='x').name)"
rm -rf /tmp/clir-wheel-test
```

Expected: `OK x`.

- [ ] **Step 5: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/scripts/build-wheel.sh web/public/wheels/.gitkeep web/.gitignore
git commit -m "feat(web): add clir wheel build script"
```

---

## Task 4: Example metadata schema and first example (hello-world)

**Files:**
- Create: `web/src/examples/hello-world/code.py`
- Create: `web/src/examples/hello-world/meta.json`
- Create: `web/src/lib/examples.ts`

This sets the pattern. Subsequent tasks add the other 18 examples following this exact shape.

- [ ] **Step 1: Create `web/src/examples/hello-world/code.py`**

```python
from clir.output import success, info, warning, error

success("Hello, world!")
info("Welcome to clir.")
warning("This is a warning.")
error("This is an error.")
```

- [ ] **Step 2: Create `web/src/examples/hello-world/meta.json`**

```json
{
  "slug": "hello-world",
  "title": "Hello, world!",
  "section": "Getting Started",
  "order": 1,
  "description": "The simplest possible clir program: print styled output."
}
```

- [ ] **Step 3: Create `web/src/lib/examples.ts`**

```ts
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EXAMPLES_DIR = path.resolve(__dirname, "..", "examples");

export interface ExampleMeta {
  slug: string;
  title: string;
  section: string;
  order: number;
  description: string;
}

export interface Example extends ExampleMeta {
  code: string;
  outputHtml: string | null; // null if pre-render not yet run
}

export function loadAllExamples(): Example[] {
  const slugs = fs
    .readdirSync(EXAMPLES_DIR)
    .filter((name) => fs.statSync(path.join(EXAMPLES_DIR, name)).isDirectory());

  const examples: Example[] = slugs.map((slug) => {
    const dir = path.join(EXAMPLES_DIR, slug);
    const meta = JSON.parse(
      fs.readFileSync(path.join(dir, "meta.json"), "utf-8"),
    ) as ExampleMeta;
    const code = fs.readFileSync(path.join(dir, "code.py"), "utf-8");
    const htmlPath = path.join(dir, "output.html");
    const outputHtml = fs.existsSync(htmlPath)
      ? fs.readFileSync(htmlPath, "utf-8")
      : null;
    return { ...meta, code, outputHtml };
  });

  examples.sort((a, b) => a.order - b.order);
  return examples;
}

export function loadExample(slug: string): Example | null {
  const all = loadAllExamples();
  return all.find((e) => e.slug === slug) ?? null;
}
```

- [ ] **Step 4: Smoke test the loader**

```bash
cd /Users/dylan/Developer/clir/web
node --input-type=module -e "
  import('./src/lib/examples.ts').then(m => {
    console.log(m.loadAllExamples());
  });
" 2>&1 | head -20
```

(If the inline import errors with a TS-resolution complaint, try `npx tsx -e ...` instead. If neither works, skip this step and rely on the build-time validation in Task 5.)

Expected: prints an array with one example whose slug is `hello-world` and `outputHtml` is `null`.

- [ ] **Step 5: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/src/examples/ web/src/lib/examples.ts
git commit -m "feat(web): add example metadata loader and hello-world example"
```

---

## Task 5: Build-time pre-renderer

**Files:**
- Create: `web/scripts/prerender-docs.mjs`

Runs each example through the venv's clir, captures stdout+stderr, converts to HTML, writes `output.html` next to `code.py`.

- [ ] **Step 1: Create `web/scripts/prerender-docs.mjs`**

```js
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

# Force rich to emit truecolor ANSI even though we're not on a TTY.
import clir.output.style as _style

stdout_buf = io.StringIO()
stderr_buf = io.StringIO()

with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
    # Re-patch consoles to point to the redirected streams (post-redirect).
    _style.console = Console(file=sys.stdout, force_terminal=True, color_system="truecolor", width=100)
    _style._stderr_console = Console(file=sys.stderr, force_terminal=True, color_system="truecolor", width=100)
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
```

- [ ] **Step 2: Run the pre-renderer**

```bash
cd /Users/dylan/Developer/clir/web
npm install --save-dev tsx
node scripts/prerender-docs.mjs
```

Expected: `✓ hello-world` and a single `Pre-render: 1 example(s) OK.` line.

- [ ] **Step 3: Verify the output file**

```bash
cat /Users/dylan/Developer/clir/web/src/examples/hello-world/output.html
```

Expected: HTML containing `<pre class="ansi">` and styled spans for the four output lines (success, info, warning, error). The error and warning content should be in the stderr-mark wrapped div.

- [ ] **Step 4: Add `output.html` files to `web/.gitignore`**

Append to `web/.gitignore`:

```
src/examples/*/output.html
```

These are build artifacts; they regenerate from `code.py` + the converter.

- [ ] **Step 5: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/scripts/prerender-docs.mjs web/package.json web/package-lock.json web/.gitignore
git commit -m "feat(web): add build-time docs pre-renderer"
```

---

## Task 6: Base Layout component + landing page (real)

**Files:**
- Create: `web/src/components/Layout.astro`
- Modify: `web/src/pages/index.astro`

- [ ] **Step 1: Create `web/src/components/Layout.astro`**

```astro
---
interface Props {
  title: string;
  description?: string;
}
const { title, description = "A modern CLI toolkit for Python." } = Astro.props;
const base = import.meta.env.BASE_URL;
---

<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <meta name="description" content={description} />
    <link
      rel="preconnect"
      href="https://fonts.googleapis.com"
    />
    <link
      rel="preconnect"
      href="https://fonts.gstatic.com"
      crossorigin
    />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=JetBrains+Mono:wght@400;700&display=swap"
    />
  </head>
  <body class="min-h-screen flex flex-col">
    <header class="border-b border-ink-50/10">
      <div class="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
        <a href={base} class="font-mono text-lg font-bold tracking-tight">clir</a>
        <nav class="flex gap-6 text-sm">
          <a href={`${base}/docs`} class="hover:text-accent transition">Docs</a>
          <a href={`${base}/playground`} class="hover:text-accent transition">Playground</a>
          <a
            href="https://github.com/exec/clir"
            class="hover:text-accent transition"
            target="_blank"
            rel="noopener noreferrer">GitHub</a>
        </nav>
      </div>
    </header>
    <main class="flex-1">
      <slot />
    </main>
    <footer class="border-t border-ink-50/10 mt-12">
      <div class="max-w-5xl mx-auto px-6 py-6 text-sm opacity-60">
        clir · MIT licensed · <a href="https://github.com/exec/clir" class="underline hover:text-accent">github.com/exec/clir</a>
      </div>
    </footer>
    <style>
      .ansi { background:#000; color:#e5e5e5; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; line-height: 1.5; }
      .ansi-bold { font-weight: 700; }
      .ansi-dim { opacity: 0.6; }
      .ansi-italic { font-style: italic; }
      .ansi-underline { text-decoration: underline; }
      .stderr-mark { border-left: 2px solid #ef4444; padding-left: 0.5rem; margin-top: 0.25rem; }
    </style>
  </body>
</html>
```

- [ ] **Step 2: Replace `web/src/pages/index.astro`**

```astro
---
import Layout from "../components/Layout.astro";
import "../styles/global.css";

const base = import.meta.env.BASE_URL;
---

<Layout title="clir — modern CLI toolkit for Python">
  <section class="max-w-3xl mx-auto px-6 py-20 text-center">
    <h1 class="text-6xl font-bold tracking-tight">clir</h1>
    <p class="mt-6 text-xl opacity-70">
      A modern CLI toolkit for building beautiful terminal applications in Python.
    </p>
    <pre class="ansi mt-10 inline-block text-left"><span>$ pip install clir</span></pre>
    <div class="mt-10 flex justify-center gap-4">
      <a href={`${base}/docs`} class="px-5 py-3 rounded-lg bg-accent text-ink-900 font-medium hover:bg-accent-dark transition">Browse the docs →</a>
      <a href={`${base}/playground`} class="px-5 py-3 rounded-lg border border-ink-50/20 hover:border-accent transition">Open the playground</a>
    </div>
  </section>
</Layout>
```

- [ ] **Step 3: Verify dev server**

```bash
cd /Users/dylan/Developer/clir/web
npm run dev -- --host 127.0.0.1 --port 4321 &
sleep 3
curl -sf http://127.0.0.1:4321/clir/ | grep -E "Browse the docs|Open the playground"
kill %1
```

Expected: both substrings present.

- [ ] **Step 4: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/src/components/Layout.astro web/src/pages/index.astro
git commit -m "feat(web): add Layout component and landing page"
```

---

## Task 7: Add the remaining 18 examples

**Files:** 18 example folders under `web/src/examples/`

Bundles all examples into one task. Each is small and self-contained. The pre-renderer (Task 5) regenerates `output.html` for all of them.

- [ ] **Step 1: Create example folders**

For each (slug, code, meta) triple below, create `web/src/examples/<slug>/code.py` and `web/src/examples/<slug>/meta.json`.

**`styled-output`** (order 2, section "Output")

`code.py`:
```python
from clir.output import echo, success, info, warning, error, debug
from clir.runtime import set_verbosity, Verbosity

set_verbosity(Verbosity(debug=True))
echo("Plain echo line.")
success("Operation completed successfully.")
info("Loaded 42 records.")
warning("Cache is stale.")
error("Connection refused.")
debug("Internal state: idle")
```

`meta.json`:
```json
{"slug": "styled-output", "title": "Styled output", "section": "Output", "order": 2, "description": "The six core output functions, with --debug enabled to show debug() too."}
```

**`tables`** (order 3, section "Output")

`code.py`:
```python
from clir.output import Table

t = Table("Component", "Status", "Latency")
t.add_row("API", "[green]running[/green]", "12ms")
t.add_row("Database", "[green]running[/green]", "3ms")
t.add_row("Cache", "[yellow]degraded[/yellow]", "84ms")
t.add_row("Queue", "[red]down[/red]", "—")
t.show()
```

`meta.json`:
```json
{"slug": "tables", "title": "Tables", "section": "Output", "order": 3, "description": "Tables with styled cells using inline rich markup."}
```

**`panels`** (order 4, section "Output")

`code.py`:
```python
from clir.output import Panel

Panel(
    "All systems operational.\n4 services healthy.",
    title="Status",
).show()
```

`meta.json`:
```json
{"slug": "panels", "title": "Panels", "section": "Output", "order": 4, "description": "Bordered panels with titles for grouping output."}
```

**`trees`** (order 5, section "Output")

`code.py`:
```python
from clir.output import Tree

t = Tree("project")
src = t.add("src")
src.add("main.py")
src.add("utils.py")
tests = t.add("tests")
tests.add("test_main.py")
t.add("README.md")
t.show()
```

`meta.json`:
```json
{"slug": "trees", "title": "Trees", "section": "Output", "order": 5, "description": "Hierarchical tree output."}
```

**`spinners-progress`** (order 6, section "Output")

`code.py`:
```python
from clir.output import Spinner, Progress
import time

with Spinner("Loading data..."):
    time.sleep(0.3)

with Progress("Indexing files", total=4) as p:
    for _ in range(4):
        time.sleep(0.05)
        p.advance()
```

`meta.json`:
```json
{"slug": "spinners-progress", "title": "Spinners & Progress", "section": "Output", "order": 6, "description": "Animated indicators (only the final frame shows in the docs; full animation in the playground)."}
```

**`markdown`** (order 7, section "Output")

`code.py`:
```python
from clir.output import Markdown

Markdown("""# Welcome
This is **bold** and *italic*.

- bullet one
- bullet two

> A blockquote.
""").show()
```

`meta.json`:
```json
{"slug": "markdown", "title": "Markdown", "section": "Output", "order": 7, "description": "Rich-rendered Markdown output."}
```

**`json-output`** (order 8, section "Output")

`code.py`:
```python
from clir.output import json

json({"status": "ok", "count": 3, "items": ["a", "b", "c"]})
```

`meta.json`:
```json
{"slug": "json-output", "title": "JSON output", "section": "Output", "order": 8, "description": "Pretty-printed JSON with syntax highlighting."}
```

**`prompts-static`** (order 9, section "Prompts")

`code.py`:
```python
# In docs we render a static representation; the playground will
# bridge actual prompt() calls to a DOM input widget.
from clir.output import Panel, info

Panel(
    "$ name = prompt(\"What is your name?\")\n"
    "  > World\n"
    "$ confirm(\"Continue?\", default=True)\n"
    "  > Y\n"
    "$ select(\"Pick a color:\", [\"red\", \"green\", \"blue\"])\n"
    "  > red",
    title="Interactive prompts (open in playground to try)",
).show()
info("clir's prompt API is non-blocking and integrates with prompt_toolkit.")
```

`meta.json`:
```json
{"slug": "prompts-static", "title": "Prompts", "section": "Prompts", "order": 9, "description": "A static walkthrough; open in the playground to actually type input. Full prompt bridging arrives in the next site update."}
```

**`wizards-static`** (order 10, section "Prompts")

`code.py`:
```python
from clir.output import Panel

Panel(
    "Step 1/3: project name → my-app\n"
    "Step 2/3: language    → Python\n"
    "Step 3/3: use a database? → Yes\n\n"
    "Result: {'name': 'my-app', 'language': 'Python', 'database': 'Yes'}",
    title="Wizard (multi-step prompt flow)",
).show()
```

`meta.json`:
```json
{"slug": "wizards-static", "title": "Wizards", "section": "Prompts", "order": 10, "description": "Multi-step interactive flows. Static depiction in docs."}
```

**`commands-groups`** (order 11, section "Framework")

`code.py`:
```python
from clir import ClirApp, argument, option

app = ClirApp(name="mycli", description="A small CLI demonstrating commands and groups.")

@app.command()
@argument("name")
@option("--count", "-c", default=1)
def greet(name: str, count: int):
    """Greet someone warmly."""
    for _ in range(count):
        print(f"Hello, {name}!")

@app.group()
def db():
    """Database operations."""
    pass

@db.command()
def migrate():
    """Run pending migrations."""
    print("Migrations applied.")

app.run(["--help"])
```

`meta.json`:
```json
{"slug": "commands-groups", "title": "Commands & Groups", "section": "Framework", "order": 11, "description": "@app.command(), @app.group(), --help, and arguments/options."}
```

**`aliases`** (order 12, section "Framework")

`code.py`:
```python
from clir import ClirApp

app = ClirApp(name="mycli")

@app.command()
def hello():
    print("Hello!")

app.aliases.add("hi", "hello")
app.aliases.add("greet", "hello")

print("Resolved 'hi' →", app.aliases.resolve("hi"))
print("Resolved 'greet' →", app.aliases.resolve("greet"))
app.run(["hi"])
```

`meta.json`:
```json
{"slug": "aliases", "title": "Aliases", "section": "Framework", "order": 12, "description": "Command shortcuts that resolve before dispatch."}
```

**`async-commands`** (order 13, section "Framework")

`code.py`:
```python
import asyncio
from clir import ClirApp

app = ClirApp(name="async-demo")

@app.command()
async def fetch(url: str = "https://example.com"):
    """Async command — runs on the same event loop as run_async."""
    await asyncio.sleep(0.05)
    print(f"Fetched {url}")

asyncio.run(app.run_async(["fetch"]))
```

`meta.json`:
```json
{"slug": "async-commands", "title": "Async commands", "section": "Framework", "order": 13, "description": "await app.run_async() works from inside an existing event loop."}
```

**`errors`** (order 14, section "Framework")

`code.py`:
```python
from clir import ClirApp, ClirError, UsageError

app = ClirApp(name="demo")

@app.command()
def bad():
    raise UsageError("Missing required --name flag.")

try:
    app.run(["bad"])
except SystemExit as e:
    print(f"\\nExit code was: {e.code}")
```

`meta.json`:
```json
{"slug": "errors", "title": "Errors", "section": "Framework", "order": 14, "description": "ClirError + UsageError surface a styled message and exit code; --debug shows the traceback."}
```

**`validation`** (order 15, section "Framework")

`code.py`:
```python
from clir import BaseModel, Field, ValidationError, ClirApp
from clir.output import error

class Config(BaseModel):
    port: int = Field(ge=1, le=65535)
    host: str = "localhost"

app = ClirApp(name="serve")

@app.command()
def start(port: str, host: str = "localhost"):
    try:
        cfg = Config(port=int(port), host=host)
        print(f"Starting on {cfg.host}:{cfg.port}")
    except ValidationError as e:
        for err in e.errors():
            error(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}")

app.run(["start", "99999"])
```

`meta.json`:
```json
{"slug": "validation", "title": "Validation", "section": "Framework", "order": 15, "description": "Pydantic validation errors are surfaced per-field via the dispatcher."}
```

**`config-files`** (order 16, section "Framework")

`code.py`:
```python
import json, tempfile, os
from clir import ClirApp

# Write a temp config and load it
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump({"debug": True, "port": 8080}, f)
    cfg_path = f.name

app = ClirApp(name="myapp")
app.load_config(cfg_path)
print("debug =", app.get_config_value("debug"))
print("port  =", app.get_config_value("port"))
os.unlink(cfg_path)
```

`meta.json`:
```json
{"slug": "config-files", "title": "Config files", "section": "Framework", "order": 16, "description": "Auto-discover and load YAML / JSON / TOML config; env-var override."}
```

**`completion`** (order 17, section "Framework")

`code.py`:
```python
from clir import ClirApp

app = ClirApp(name="mycli")

@app.command()
def hello():
    pass

@app.command()
def world():
    pass

print(app.generate_completion("zsh")[:400] + "\\n... (truncated)")
```

`meta.json`:
```json
{"slug": "completion", "title": "Shell completion", "section": "Framework", "order": 17, "description": "Generate bash, zsh, or fish completion scripts."}
```

**`themes-tour`** (order 18, section "Output")

`code.py`:
```python
from clir.output import set_theme, get_console, success, Panel

for theme in ["default", "dracula", "monokai", "nord"]:
    set_theme(theme)
    success(f"--- {theme} ---")
    Panel("Hello from " + theme, title=theme).show()
```

`meta.json`:
```json
{"slug": "themes-tour", "title": "Theme tour", "section": "Output", "order": 18, "description": "A few themes side by side. Visit /themes for the full 15-theme gallery (next update)."}
```

**`plugins`** (order 19, section "Framework")

`code.py`:
```python
from clir import ClirApp
from clir.plugins import PluginManager

app = ClirApp(name="myapp")
pm = PluginManager(app)

# Register a plugin command in code (the real plugin system also discovers
# entry-point packages).
def hello_cmd():
    """Hello from a plugin."""
    print("Hello from a plugin!")

pm.register_command("hello", hello_cmd)
app.run(["hello"])
```

`meta.json`:
```json
{"slug": "plugins", "title": "Plugins", "section": "Framework", "order": 19, "description": "Register additional commands at runtime via the plugin manager."}
```

- [ ] **Step 2: Run the pre-renderer for all examples**

```bash
cd /Users/dylan/Developer/clir/web
node scripts/prerender-docs.mjs
```

Expected: 19 `✓` lines and `Pre-render: 19 example(s) OK.`. If any fail, fix the example's `code.py` so it runs cleanly under the venv (some examples may need adjustment if the actual clir API differs from what's in the snippet — favor making the snippet match clir's real API, NOT modifying clir).

If a particular API mismatch (e.g., `Panel`'s constructor signature, `pm.register_command`) causes the example to fail, simplify the example or document the actual API shape inline. The goal is "every example runs"; clir's API is the source of truth.

- [ ] **Step 3: Spot-check three examples**

```bash
ls /Users/dylan/Developer/clir/web/src/examples/*/output.html | wc -l  # expect 19
head -3 /Users/dylan/Developer/clir/web/src/examples/tables/output.html
head -3 /Users/dylan/Developer/clir/web/src/examples/themes-tour/output.html
```

- [ ] **Step 4: Commit (code only — output.html files are gitignored)**

```bash
cd /Users/dylan/Developer/clir
git add web/src/examples/
git commit -m "feat(web): add 18 more clir examples"
```

---

## Task 8: Docs page with all examples

**Files:**
- Create: `web/src/components/Sidebar.astro`
- Create: `web/src/components/CodeBlock.astro`
- Create: `web/src/pages/docs.astro`

- [ ] **Step 1: Create `web/src/components/CodeBlock.astro`**

```astro
---
interface Props {
  code: string;
  outputHtml: string;
  slug: string;
}
const { code, outputHtml, slug } = Astro.props;
const base = import.meta.env.BASE_URL;
---

<div class="code-block rounded-lg border border-ink-50/10 overflow-hidden mt-4 mb-8">
  <div class="flex border-b border-ink-50/10 bg-ink-900/40">
    <button class="tab px-4 py-2 text-sm font-medium" data-tab="output" data-slug={slug}>Output</button>
    <button class="tab px-4 py-2 text-sm opacity-60 hover:opacity-100" data-tab="code" data-slug={slug}>Code</button>
    <a
      href={`${base}/playground?example=${slug}`}
      class="ml-auto px-4 py-2 text-sm hover:text-accent transition"
    >▷ Open in Playground</a>
  </div>
  <div class="tab-panel" data-panel="output" data-slug={slug} set:html={outputHtml} />
  <div class="tab-panel hidden" data-panel="code" data-slug={slug}>
    <pre class="ansi"><code>{code}</code></pre>
  </div>
</div>

<script define:vars={{ slug }}>
  const buttons = document.querySelectorAll(`[data-slug="${slug}"][data-tab]`);
  const panels = document.querySelectorAll(`[data-slug="${slug}"][data-panel]`);
  buttons.forEach((b) => {
    b.addEventListener("click", () => {
      const target = b.dataset.tab;
      buttons.forEach((bb) => bb.classList.toggle("opacity-60", bb.dataset.tab !== target));
      panels.forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== target));
    });
  });
</script>
```

- [ ] **Step 2: Create `web/src/components/Sidebar.astro`**

```astro
---
import { loadAllExamples } from "../lib/examples";
const examples = loadAllExamples();
const sections: Record<string, { slug: string; title: string }[]> = {};
for (const e of examples) {
  if (!sections[e.section]) sections[e.section] = [];
  sections[e.section].push({ slug: e.slug, title: e.title });
}
---

<aside class="sticky top-4 self-start text-sm">
  <nav class="space-y-6">
    {Object.entries(sections).map(([sectionName, items]) => (
      <div>
        <div class="font-semibold opacity-60 uppercase tracking-wider text-xs">{sectionName}</div>
        <ul class="mt-2 space-y-1">
          {items.map((it) => (
            <li><a href={`#${it.slug}`} class="hover:text-accent transition">{it.title}</a></li>
          ))}
        </ul>
      </div>
    ))}
  </nav>
</aside>
```

- [ ] **Step 3: Create `web/src/pages/docs.astro`**

```astro
---
import Layout from "../components/Layout.astro";
import Sidebar from "../components/Sidebar.astro";
import CodeBlock from "../components/CodeBlock.astro";
import { loadAllExamples } from "../lib/examples";
import "../styles/global.css";

const examples = loadAllExamples();
---

<Layout title="clir docs">
  <div class="max-w-6xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-10">
    <Sidebar />
    <article class="prose prose-invert max-w-none space-y-12">
      <header>
        <h1 class="text-4xl font-bold tracking-tight">Documentation</h1>
        <p class="opacity-70 mt-2">Every clir feature, with character-perfect rendered output. Click "Open in Playground" on any example to edit and re-run.</p>
      </header>

      {examples.map((ex) => (
        <section id={ex.slug}>
          <h2 class="text-2xl font-semibold mt-12">{ex.title}</h2>
          <p class="opacity-70 mt-1">{ex.description}</p>
          {ex.outputHtml ? (
            <CodeBlock code={ex.code} outputHtml={ex.outputHtml} slug={ex.slug} />
          ) : (
            <div class="mt-4 px-4 py-3 rounded border border-yellow-500/30 text-yellow-200 text-sm">
              Output not pre-rendered. Run <code>npm run build</code> first.
            </div>
          )}
        </section>
      ))}
    </article>
  </div>
</Layout>
```

- [ ] **Step 4: Run build + serve, spot-check**

```bash
cd /Users/dylan/Developer/clir/web
npm run build
npx --yes http-server dist -p 4322 -s &
sleep 2
curl -sf http://127.0.0.1:4322/clir/docs/ | grep -E "Hello, world|Tables|Async commands" | head -5
kill %1
```

Expected: at least three feature titles present in the rendered HTML.

- [ ] **Step 5: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/src/components/Sidebar.astro web/src/components/CodeBlock.astro web/src/pages/docs.astro
git commit -m "feat(web): docs page with sidebar TOC and all 19 examples"
```

---

## Task 9: Pyodide bootstrap module

**Files:**
- Create: `web/src/lib/pyodide.ts`

- [ ] **Step 1: Create `web/src/lib/pyodide.ts`**

```ts
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
    const base = (import.meta as ImportMeta & { env: { BASE_URL: string } }).env.BASE_URL;
    const baseClean = base.endsWith("/") ? base : base + "/";
    const wheelDir = `${window.location.origin}${baseClean}wheels/`;
    // Discover the wheel filename (we ship exactly one).
    const wheelListUrl = `${baseClean}wheels-list.json`;
    let wheelFilename: string;
    try {
      const r = await fetch(wheelListUrl);
      if (!r.ok) throw new Error("no wheel list");
      const list = (await r.json()) as { wheels: string[] };
      wheelFilename = list.wheels[0];
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
import io
from rich.console import Console
import clir.output.style as _style
_style.console = Console(file=sys.stdout, force_terminal=True, color_system="truecolor", width=100)
_style._stderr_console = Console(file=sys.stderr, force_terminal=True, color_system="truecolor", width=100)

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
```

- [ ] **Step 2: Generate `wheels-list.json` during build**

In `web/scripts/build-wheel.sh`, append (right after the wheel is copied):

```bash
# Update the wheels-list.json so the playground can discover the filename.
node -e "
  const fs = require('fs');
  const path = require('path');
  const dir = path.resolve('$WHEEL_DIR');
  const wheels = fs.readdirSync(dir).filter(f => f.endsWith('.whl'));
  fs.writeFileSync(path.join(path.dirname(dir), 'wheels-list.json'), JSON.stringify({wheels}));
"
```

(Note: `path.dirname(dir)` puts `wheels-list.json` at `web/public/wheels-list.json` — sibling of `wheels/`. The fetch path in `pyodide.ts` already expects this.)

- [ ] **Step 3: Re-run wheel build**

```bash
cd /Users/dylan/Developer/clir
bash web/scripts/build-wheel.sh
ls web/public/wheels-list.json && cat web/public/wheels-list.json
```

Expected: `{"wheels":["clir-0.1.0-py3-none-any.whl"]}` (or current version).

- [ ] **Step 4: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/src/lib/pyodide.ts web/scripts/build-wheel.sh web/public/wheels-list.json
git commit -m "feat(web): add Pyodide bootstrap and clir wheel discovery"
```

---

## Task 10: Playground page with Monaco editor

**Files:**
- Create: `web/src/components/Playground.tsx`
- Create: `web/src/pages/playground.astro`

- [ ] **Step 1: Add Monaco dep**

```bash
cd /Users/dylan/Developer/clir/web
npm install @monaco-editor/loader monaco-editor
```

- [ ] **Step 2: Create `web/src/components/Playground.tsx`**

This is a Preact island. It loads Pyodide on first Run, hosts Monaco as the editor, and renders captured output through the same ANSI converter the docs use.

```tsx
import { useEffect, useRef, useState } from "preact/hooks";
import { ansiToHtml } from "../lib/ansi";
import { runPython } from "../lib/pyodide";
import loader from "@monaco-editor/loader";

const DEFAULT_CODE = `from clir.output import success, info

success("Hello from the playground!")
info("Click Run to execute this Python in your browser.")
`;

interface Props {
  initialCode?: string;
}

export default function Playground({ initialCode }: Props) {
  const [code, setCode] = useState<string>(initialCode ?? DEFAULT_CODE);
  const [outputHtml, setOutputHtml] = useState<string>("");
  const [status, setStatus] = useState<string>("Ready");
  const [running, setRunning] = useState<boolean>(false);
  const editorContainer = useRef<HTMLDivElement>(null);
  const editorRef = useRef<unknown>(null);

  // Restore from URL hash or localStorage on mount.
  useEffect(() => {
    const hash = window.location.hash;
    const m = /#code=([^&]+)/.exec(hash);
    if (m) {
      try {
        const decoded = atob(decodeURIComponent(m[1]));
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
        runHandler();
      });
    });
    return () => { disposed = true; };
  }, []);

  // Sync external code changes (e.g., from URL hash) into Monaco.
  useEffect(() => {
    const e = editorRef.current as { getValue: () => string; setValue: (v: string) => void } | null;
    if (e && e.getValue() !== code) e.setValue(code);
  }, [code]);

  async function runHandler(): Promise<void> {
    if (running) return;
    setRunning(true);
    setStatus("Booting Python (first run takes a few seconds)...");
    try {
      const result = await runPython(code);
      setStatus(result.error ? "Run completed with errors" : "Run complete");
      const stdout = ansiToHtml(result.stdout);
      const stderr = result.stderr ? `<div class="stderr-mark">${ansiToHtml(result.stderr)}</div>` : "";
      const errorBlock = result.error
        ? `<pre class="ansi" style="color:#ef4444">${result.error.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</pre>`
        : "";
      setOutputHtml(stdout + stderr + errorBlock);
    } catch (e) {
      setStatus(`Failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[calc(100vh-200px)]">
      <div class="flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm opacity-70">Editor (Cmd/Ctrl+Enter to run)</span>
          <button
            onClick={runHandler}
            disabled={running}
            class="px-4 py-1.5 rounded bg-accent text-ink-900 font-medium disabled:opacity-50 hover:bg-accent-dark transition"
          >{running ? "Running..." : "▶ Run"}</button>
        </div>
        <div ref={editorContainer} class="flex-1 border border-ink-50/10 rounded overflow-hidden" />
      </div>
      <div class="flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm opacity-70">Output</span>
          <span class="text-xs opacity-50">{status}</span>
        </div>
        <div
          class="flex-1 border border-ink-50/10 rounded overflow-auto bg-black p-2"
          dangerouslySetInnerHTML={{
            __html: outputHtml || `<div class="text-ink-50/30 text-sm p-2">Click Run to execute.</div>`,
          }}
        />
      </div>
    </div>
  );
}
```

(Note: Preact uses `class` attribute, not `className`. Astro JSX with the Preact integration accepts both, but `class` keeps things consistent across `.astro` and `.tsx`.)

- [ ] **Step 3: Create `web/src/pages/playground.astro`**

```astro
---
import Layout from "../components/Layout.astro";
import Playground from "../components/Playground.tsx";
import { loadExample } from "../lib/examples";
import "../styles/global.css";

const url = Astro.url;
const exampleSlug = url.searchParams.get("example") ?? null;
const initialCode = exampleSlug ? loadExample(exampleSlug)?.code ?? null : null;
---

<Layout title="clir playground">
  <section class="max-w-7xl mx-auto px-6 py-6">
    <h1 class="text-2xl font-semibold mb-2">Playground</h1>
    <p class="opacity-70 mb-6 text-sm">
      Real Python in your browser. First run boots Pyodide and installs the clir wheel — takes a few seconds.
    </p>
    <Playground client:load initialCode={initialCode} />
  </section>
</Layout>
```

- [ ] **Step 4: Test the playground in dev**

```bash
cd /Users/dylan/Developer/clir/web
npm run dev -- --host 127.0.0.1 --port 4321 &
sleep 3
curl -sf http://127.0.0.1:4321/clir/playground/ | grep -E "Playground|Run" | head -5
kill %1
```

Expected: substrings present. Manual browser test: visit `http://127.0.0.1:4321/clir/playground/`, click Run, wait for Pyodide to load (~5-10s first time), confirm "Hello from the playground!" appears in the output pane.

- [ ] **Step 5: Commit**

```bash
cd /Users/dylan/Developer/clir
git add web/src/components/Playground.tsx web/src/pages/playground.astro web/package.json web/package-lock.json
git commit -m "feat(web): playground page with Monaco editor and Pyodide runtime"
```

---

## Task 11: Wire "Open in Playground" links

The CodeBlock component (Task 8) already includes `?example=<slug>` query-param links. The Playground page (Task 10) already reads that query param via `loadExample`. Verify end-to-end:

- [ ] **Step 1: Build and verify**

```bash
cd /Users/dylan/Developer/clir/web
npm run build
ls dist/playground/index.html
```

Expected: build succeeds.

- [ ] **Step 2: Manual browser smoke test**

```bash
cd /Users/dylan/Developer/clir/web
npx --yes http-server dist -p 4322 -s &
sleep 2
echo "Visit http://127.0.0.1:4322/clir/docs/ — click 'Open in Playground' on any example."
echo "Confirm the playground opens with that example's code preloaded."
echo "Kill server with: kill %1"
```

User runs this manually; the implementer subagent skips Step 2 if running headlessly.

- [ ] **Step 3: No commit needed if no code changed**

This task validates wiring. If anything was missing, commit the fix here.

---

## Task 12: GitHub Actions deploy workflow

**Files:**
- Create: `.github/workflows/deploy-site.yml`

- [ ] **Step 1: Create `.github/workflows/deploy-site.yml`**

```yaml
name: Deploy site

on:
  push:
    branches: [main]
    paths:
      - "clir/**"
      - "web/**"
      - "pyproject.toml"
      - ".github/workflows/deploy-site.yml"
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: deploy-site
  cancel-in-progress: true

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Set up venv and install clir + build
        run: |
          python -m venv .venv
          .venv/bin/pip install --upgrade pip
          .venv/bin/pip install -e ".[dev]" build

      - name: Build clir wheel
        run: bash web/scripts/build-wheel.sh

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: web/package-lock.json

      - name: Install web deps
        run: cd web && npm ci

      - name: Run vitest
        run: cd web && npm run test

      - name: Pre-render docs
        run: cd web && node scripts/prerender-docs.mjs

      - name: Astro build
        run: cd web && npx astro build

      - name: Deploy to gh-pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: web/dist
          force_orphan: true
```

- [ ] **Step 2: Commit**

```bash
cd /Users/dylan/Developer/clir
git add .github/workflows/deploy-site.yml
git commit -m "ci: add GitHub Actions workflow to deploy site to gh-pages"
```

- [ ] **Step 3: Configure GitHub Pages source (manual)**

The implementer notes this for the human controller:
- After this commit pushes to `main`, the workflow runs once and creates the `gh-pages` branch.
- Then on GitHub: Repo → Settings → Pages → Source = `gh-pages` branch, `/` folder.
- Site lives at `https://exec.github.io/clir/` after first successful run.

The implementer subagent does NOT touch GitHub settings; that's the human's job after merge.

---

## Task 13: Final integration smoke

**Files:** none (verification only)

- [ ] **Step 1: Full local build + tests**

```bash
cd /Users/dylan/Developer/clir/web
npm run test
npm run build
ls dist/index.html dist/docs/index.html dist/playground/index.html
```

Expected: tests pass; all three HTML files exist.

- [ ] **Step 2: Manual smoke test**

```bash
cd /Users/dylan/Developer/clir/web
npx --yes http-server dist -p 4322 -s &
sleep 2
echo "Visit http://127.0.0.1:4322/clir/ — verify landing page renders"
echo "Visit http://127.0.0.1:4322/clir/docs/ — verify all 19 examples render with output"
echo "Visit http://127.0.0.1:4322/clir/playground/ — verify editor loads and Run works"
echo "From docs, click any 'Open in Playground' button — verify it preloads the code"
echo "Kill server with: kill %1"
```

- [ ] **Step 3: Verify final commit log**

```bash
git log --oneline | head -16
```

Expected: ~12 commits for this plan, on top of the Phase 2 commits.

- [ ] **Step 4: Capture final HEAD**

```bash
git rev-parse HEAD
```

Record for the deploy step.

---

## Out of scope (Plan 2)

- Theme switcher across docs and runtime theme switching in playground.
- `/themes` gallery page.
- Prompt bridging in playground (`prompt`, `confirm`, `select`, `multiselect`, `autocomplete`, `password`).
- Wizard interactivity in playground.
- Hero animation on landing.
- `--debug` traceback walkthrough in docs.
- Self-hosting Pyodide (currently CDN-loaded).
- Visual regression CI (fixtures + hash compare).
- Share-URL hash encoding (basic implementation present; full UX in Plan 2).
- Astro Shiki integration for syntax-highlighted Python in code-only tab (Plan 1 uses plain `<pre>`).
