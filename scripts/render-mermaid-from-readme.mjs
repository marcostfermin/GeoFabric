import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

function die(msg) {
  console.error(msg);
  process.exit(1);
}

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: "inherit", ...opts });
  if (r.status !== 0) die(`Command failed: ${cmd} ${args.join(" ")}`);
}

const repoRoot = process.cwd();
const readmePath = path.join(repoRoot, "README.md");
if (!fs.existsSync(readmePath)) die("README.md not found");

const readme = fs.readFileSync(readmePath, "utf8");

// Extract mermaid fenced blocks: ```mermaid ... ```
const mermaidBlocks = [];
const fenceRe = /```mermaid\s*\n([\s\S]*?)\n```/g;
let match;
while ((match = fenceRe.exec(readme)) !== null) {
  const body = match[1].trimEnd();
  if (body.trim().length) mermaidBlocks.push(body);
}

if (mermaidBlocks.length === 0) {
  console.log("No Mermaid blocks found in README.md. Nothing to do.");
  process.exit(0);
}

// For your README, you have one architecture diagram; if multiple exist,
// we render them all deterministically: diagram-1.svg, diagram-2.svg, ...
const docsDir = path.join(repoRoot, "docs");
fs.mkdirSync(docsDir, { recursive: true });

const outFiles = [];
for (let i = 0; i < mermaidBlocks.length; i++) {
  const idx = i + 1;
  const mmdText = mermaidBlocks[i];

  const mmdFile = path.join(docsDir, `diagram-${idx}.mmd`);
  const svgFile = path.join(docsDir, `diagram-${idx}.svg`);

  fs.writeFileSync(mmdFile, mmdText + "\n", "utf8");

  // Render using mermaid-cli (mmdc)
  run("mmdc", ["-i", mmdFile, "-o", svgFile, "-b", "transparent"]);

  outFiles.push({ idx, mmdFile, svgFile });
}

console.log(`Rendered ${outFiles.length} Mermaid diagram(s) to docs/*.svg.`);

// OPTIONAL README rewrite logic:
// - Replace the first Mermaid block with an <img> tag + <details> containing the source.
// - Leave additional Mermaid blocks untouched (or extend similarly).
//
// This is the most PyPI-friendly pattern.
const first = outFiles[0];
const imgRelative = `https://raw.githubusercontent.com/marcostfermin/GeoFabric/main/docs/diagram-${first.idx}.svg`;

// Build replacement that preserves Mermaid source for GitHub readers
const replacement =
  [
    "",
    "<!-- Rendered diagram (PyPI-friendly) -->",
    `<img src="${imgRelative}" alt="Architecture diagram" width="900" />`,
    "",
    "<details>",
    "<summary>Mermaid source</summary>",
    "",
    "```mermaid",
    mermaidBlocks[0].trimEnd(),
    "```",
    "",
    "</details>",
    ""
  ].join("\n");

// Replace only the first Mermaid fenced block occurrence
const rewritten = readme.replace(/```mermaid\s*\n[\s\S]*?\n```/, replacement);

if (rewritten !== readme) {
  fs.writeFileSync(readmePath, rewritten, "utf8");
  console.log("Updated README.md to use rendered SVG (kept Mermaid source in <details>).");
} else {
  console.log("README.md not modified (unexpected: replacement did not apply).");
}
