import fs from "node:fs";
import path from "node:path";

// Resolve relative to the web/ project root (process.cwd() during both
// `astro build` and `vitest`). Using import.meta.url breaks at build time
// because Astro bundles this module into dist/, where the relative path
// to the source examples/ directory no longer holds.
const EXAMPLES_DIR = path.resolve(process.cwd(), "src", "examples");

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
