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
