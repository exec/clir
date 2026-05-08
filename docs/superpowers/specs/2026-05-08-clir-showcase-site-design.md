# Clir Showcase Site Design

**Date:** 2026-05-08
**Scope:** Marketing/playground site for the `clir` Python CLI toolkit. GitHub Pages-hosted, designed for eventual migration to self-hosting.

## Goal

Drive adoption of `clir` by letting visitors experience its output and feature surface end-to-end without installing anything. Specifically:

- Character- and color-perfect rendering of every clir output component (Tables, Panels, Trees, Spinners, themes, etc.) in the browser.
- Code snippets that exactly match the rendered output.
- A real Python runtime in the browser so visitors can edit and run actual `clir` code.
- Documentation organized by feature, with a one-click path from any example into an editable playground.

## Non-goals

- Multi-file editor in the playground.
- Installing arbitrary PyPI packages from inside the playground.
- Backend persistence, accounts, collaboration.
- Analytics or telemetry.
- Replacing the project README. The site is for showcasing; the README stays authoritative for install/contribute info.

## Architecture

### Stack

| Layer            | Choice                                                                |
|------------------|-----------------------------------------------------------------------|
| Site generator   | **Astro** — content-first, hydrated islands for interactivity.        |
| Styling          | **Tailwind** — utility CSS.                                           |
| Editor           | **Monaco** — Python syntax + clir-aware typings for autocomplete.     |
| Python runtime   | **Pyodide** ≥ 0.27 (CPython compiled to WASM).                        |
| Clir distribution| Wheel built from this repo, hosted at `/wheels/clir-{version}.whl`.   |
| Output renderer  | Custom DOM-based ANSI→HTML translator (no xterm.js).                  |
| CI / deploy      | GitHub Actions → `gh-pages` branch.                                   |

### Repo layout

The site lives in `web/` at repo root, isolated from the Python package:

```
clir/                  # Python package (existing)
docs/                  # Existing superpowers docs
web/
  src/
    pages/             # Astro routes: index.astro, docs.astro, playground.astro, themes.astro
    components/        # Hero, Sidebar, ExampleCard, Playground, ThemeSwitcher, etc.
    examples/          # Each example as Markdown + Python snippet + metadata
    lib/
      ansi.ts          # ANSI→HTML converter
      pyodide.ts       # Pyodide bootstrap + clir wheel loading
      prompts.ts       # JS-side bridge for clir.prompts.*
  public/
    wheels/            # Built clir wheel(s)
    pyodide/           # Self-hosted Pyodide bundle
  scripts/
    build-wheel.sh     # builds clir wheel into web/public/wheels/
    prerender-docs.mjs # captures static ANSI output for docs at build time
  astro.config.mjs
  tailwind.config.mjs
  package.json
.github/
  workflows/
    deploy-site.yml    # build + push gh-pages
```

The Python package is unaffected. `web/` may be added to a `.gitignore` exclusion only for build outputs (`web/dist/`).

## Page shape

### `/` — Landing

- Hero: looping pre-rendered animation (~6s, terminal-style typing then rendering of 3 hand-picked clir features in sequence: a styled `success`/`error` line, a Table, then a themed Panel).
- One-sentence pitch + install snippet (`pip install clir`).
- Compact feature grid (8-12 cards) linking to anchored sections in `/docs`.
- "Open the playground" CTA.

### `/docs` — Long-scrolling docs

- Sticky left sidebar with TOC; main pane is the docs body; right rail (≥lg breakpoint) shows the current section's "Open in Playground" button pinned.
- Sections, in order:
  1. Hello World
  2. Styled Output (`echo`, `success`, `error`, `warning`, `info`, `debug`)
  3. Themes (overview + link to `/themes`)
  4. Tables
  5. Panels
  6. Trees
  7. Spinners & Progress
  8. Markdown rendering
  9. JSON output
  10. Prompts (`prompt`, `password`, `confirm`, `select`, `multiselect`, `autocomplete`)
  11. Wizards
  12. Commands & Groups (`@app.command()`, `@app.group()`, `--help`, typo suggestion)
  13. Aliases
  14. Async commands (`app.run_async`)
  15. Errors (`ClirError`, `UsageError`, `--debug` traceback)
  16. Validation (pydantic integration)
  17. Config files
  18. Completion (bash/zsh/fish)
  19. Plugins
- Each section: prose intro (1-3 paragraphs) + tabbed code/output block (default tab: rendered output; second tab: source) + "▷ Open in Playground" button.

### `/playground` — Interactive playground

- Fullscreen layout: left = Monaco editor; right = output pane.
- Toolbar across top: Run • Theme dropdown • Example dropdown (preloaded with the same set of examples as `/docs`) • "Share" (URL with base64-encoded source in hash) • Reset.
- Bottom of editor: status line ("Pyodide ready", "Running...", "Output captured").
- Below output: a small input affordance that appears when Python code calls `prompt()`, `select()`, etc.
- Auto-saves source buffer to `localStorage` keyed by route.
- URL-shareable via `#code=<base64>`.

### `/themes` — Theme gallery

- Grid of 15 cards, one per theme.
- Each card shows the same canonical example (a small Panel + Table + a `success` line) rendered in that theme.
- Pre-rendered at build time. No JS required to view the gallery.
- Click a card → opens `/playground` with that theme preselected.

## Rendering pipeline

This is the single most important technical decision. Two surfaces need rendered output: docs (static, instant) and playground (dynamic).

### Docs: build-time pre-rendering

- A Node build script (`scripts/prerender-docs.mjs`) runs after the wheel is built and before Astro's content collection.
- For each example in `web/src/examples/`, it spawns a CPython subprocess (the same Python that's installed in CI), `force_terminal=True`, captures stdout/stderr, and writes the captured ANSI text plus an `output.html` (run through the ANSI→HTML converter at build time).
- Astro's content layer reads these alongside the example metadata.
- Result: docs serve fully static HTML. Pyodide is never loaded for docs viewing.

The build script must capture both streams separately and preserve their interleaving so theme styling on stderr (e.g., `error()`) renders correctly.

### Playground: runtime via Pyodide

- Pyodide bundle is self-hosted at `/pyodide/`. Loaded lazily on first user interaction (clicking Run, opening Playground, or via prefetch hint after page idle).
- On first run: Pyodide bootstraps, then `micropip.install("/wheels/clir-X.Y.Z.whl")` installs clir from the local wheel.
- For each Run: stdout and stderr are captured via Python `contextlib.redirect_stdout/stderr` to `StringIO`. After execution, the captured ANSI text is fed to the same converter that builds docs.
- Stdout and stderr are rendered to one terminal pane; stderr lines may be tagged with a thin marker bar to distinguish (decision: yes — visual differentiation matters for diagnostics demos, especially `--debug` traceback walkthroughs).

### ANSI → HTML converter (`web/src/lib/ansi.ts`)

Hand-written, scoped to the SGR codes rich emits:

- Reset: `\x1b[0m`
- Bold, Dim, Italic, Underline.
- 8-color foreground/background (`\x1b[3{0-7}m`, `\x1b[4{0-7}m`).
- 256-color (`\x1b[38;5;Nm`, `\x1b[48;5;Nm`) — palette baked in.
- Truecolor (`\x1b[38;2;R;G;Bm`, `\x1b[48;2;R;G;Bm`).
- Cursor moves: clear line, move up N — used by Spinner/Progress.

Any unhandled code is consumed silently (rich also emits some safety/reset sequences that don't need rendering).

Output: a sequence of styled `<span>` runs inside a `<pre>` block with `font-family: 'JetBrains Mono', monospace; line-height: 1.4;`.

### Spinners and Progress

- These animate via cursor-control codes (clear-line, move-up). The converter has a "live" mode where each new chunk replaces the prior frame.
- The Pyodide bridge streams `sys.stdout.write` calls (not just final-output capture) into the converter, so animations play smoothly. Frame rate capped at 30 FPS to avoid thrashing.
- Static docs renderings show only the final frame (the spinner's "✓ Done" state) — Animation is exclusive to playground.

### Prompts in playground (`web/src/lib/prompts.ts`)

- `clir.prompts.*` (which uses `prompt_toolkit` — won't work in browser) is monkey-patched in Pyodide on import.
- Each prompt function becomes a sync Python call that suspends until a JS-side resolution. Implementation: Pyodide's `runPythonAsync` + a JS callback that returns a Promise; Python uses `await pyodide.ffi.create_proxy(...)` or a synchronous waiter (depending on what works cleanly with Pyodide's threading model).
- DOM widget shown in the output pane:
  - `prompt(text)` → text input.
  - `password(text)` → masked input.
  - `confirm(text, default=...)` → Yes/No buttons.
  - `select(text, choices)` → clickable list.
  - `multiselect(text, choices)` → checkbox list.
  - `autocomplete(text, completer)` → input with live suggestion dropdown driven by the Python-side completer (calls back into Pyodide on each keystroke).

### Async commands

`app.run_async(...)` works directly: Pyodide supports asyncio, and the playground's runner uses `await pyodide.runPythonAsync(...)` so any top-level `await` in user code is honored.

## Theme switcher

- Page-level theme switcher in the header (dropdown of all 15 themes).
- On `/playground`: changes propagate via re-running with `set_theme(name)` first.
- On `/themes`: not needed — gallery renders all themes side-by-side at build time.
- On `/docs`: the dropdown re-fetches a pre-rendered theme variant. To keep build size manageable, docs ship pre-rendered HTML for **two** themes only — `default` and one user-selected (defaulting to `dracula`, popular in dev tooling). Switching to other themes within docs surfaces a banner: "Open this example in the playground to try `<theme>`." This is a deliberate scope cut.

## Build & deploy

### CI workflow (`.github/workflows/deploy-site.yml`)

```yaml
on:
  push:
    branches: [main]
    paths: ["clir/**", "web/**", ".github/workflows/deploy-site.yml"]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Build wheel
        run: bash web/scripts/build-wheel.sh
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd web && npm ci
      - name: Pre-render docs outputs
        run: cd web && node scripts/prerender-docs.mjs
      - run: cd web && npm run build
      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: web/dist
```

### GitHub Pages config

- Source: `gh-pages` branch, `/` (root).
- Custom domain optional; `web/public/CNAME` controls it.

### Migration to self-hosting

The build output (`web/dist/`) is plain static HTML/CSS/JS/wasm. Move via `rsync` to any web server. Or push to a CDN. No backend pieces to migrate.

## UX details

- Editor: Monaco with Python language service. clir typings shipped alongside as a `.pyi` for autocomplete on `from clir import *`.
- "Booting Python..." spinner shown during Pyodide cold load (~3-5s on broadband).
- Output pane uses `prefers-color-scheme` for default light/dark; user theme dropdown overrides.
- Keyboard: `Cmd/Ctrl-Enter` runs in playground.
- Copy button on every code/output block.
- All examples in `/docs` are mirrored 1:1 into the playground example dropdown.

## Examples library

The set of examples lives in `web/src/examples/` as one folder per example:

```
web/src/examples/
  hello-world/
    code.py
    meta.json   # {title, slug, section, description}
    output.txt  # generated at build time
    output.html # generated at build time
```

Initial set (one per docs section, ~19 total):

1. `hello-world` — `success("Hello, world!")`
2. `styled-output` — every level + colors
3. `themes-tour` — same content rendered with `set_theme()` cycling
4. `tables` — Table with rows + a styled column
5. `panels` — Panel with a title and styled body
6. `trees` — Tree of nested nodes
7. `spinners-progress` — animated Spinner then a Progress with ETA
8. `markdown` — `Markdown("# Hello\n- a\n- b")`
9. `json-output` — `--json` mode walkthrough
10. `prompts` — text + confirm + select chained
11. `wizards` — multi-step Wizard
12. `commands-groups` — small CLI with `@app.group()` and a sub-command
13. `aliases` — alias resolution with the `--help` showing it
14. `async-commands` — `await app.run_async(["fetch", "--n", "3"])`
15. `errors` — `raise ClirError(..., exit_code=2)` with and without `--debug`
16. `validation` — pydantic ValidationError → per-field error
17. `config-files` — `app.load_config()` from a YAML string
18. `completion` — `app.print_completion("zsh")` output
19. `plugins` — register a plugin command

## Testing

- **Visual regression at build time:** the prerender script also writes `output.html` files into a fixtures dir. CI compares hashes; mismatch fails the build (forces author to update fixtures intentionally). Catches accidental render changes.
- **Pyodide smoke test:** Playwright job loads `/playground`, runs the default Hello World, asserts the output contains "Hello".
- **Astro build is the structural test:** any broken example (Python error, import error, wheel install fail) surfaces as a failed build.
- **No unit tests for the converter** in v1 — the visual-regression fixtures are the test. (Fixtures cover the SGR coverage matrix implicitly through the example library.)

## Risks and mitigations

- **Pyodide cold load is slow.** Mitigation: lazy-load on user interaction, prefetch on idle, show clear "Booting Python..." spinner. Docs themselves never wait on Pyodide.
- **Prompt bridging from Python is async-tricky.** Mitigation: gate prompts behind a clean abstraction in `prompts.ts`. If we can't make a synchronous-feel `prompt()` work cleanly within Pyodide constraints, fall back to "Prompt detected — please supply input below" UI that resumes execution after submit. Acceptable v1 degradation.
- **Spinner cursor-control rendering is fragile.** Mitigation: cap to the operations rich actually emits; document the supported codes; visual regression catches accidents.
- **Wheel size + Pyodide WASM + assets.** Mitigation: Pyodide is the heaviest by far (~6MB compressed). Self-host with long Cache-Control. clir wheel is tiny. Total cold load for playground ~7-8MB; for docs, <500kb.
- **Build determinism for visual regression.** Mitigation: pin Python version, pin clir version, freeze terminal-detection envvars in the build script.

## Phasing

The whole spec is one delivery, but a sensible internal sequence is:

1. **Foundation** — repo skeleton, build wheel, Astro project bootstrap, basic Astro page with one rendered example via build-time pre-render.
2. **Docs page** — all 19 sections with build-time output, sidebar TOC, "Open in Playground" buttons (linking to a stub).
3. **Playground (basic)** — Monaco + run + output pane + Pyodide bootstrap + lazy load. Output rendering only (no prompts).
4. **Theme switcher + /themes gallery.**
5. **Prompts & async** — bridge `clir.prompts.*` to DOM widgets.
6. **Polish** — hero animation, share URL, keyboard shortcuts, visual regression fixtures.
7. **Deploy** — GitHub Action + gh-pages + CNAME if applicable.

Each phase produces a working, testable site.
