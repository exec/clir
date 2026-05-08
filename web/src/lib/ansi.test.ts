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
