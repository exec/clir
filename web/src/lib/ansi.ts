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
