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

// Find the Mermaid block inside the "## Architecture" section.
// This prevents accidentally replacing the wrong Mermaid block if you add more later.
function extractArchitectureMermaid(md) {
  // Capture text from "## Architecture" up to the next "## " heading (or end of file).
  const sectionRe = /(^##\s+Architecture\s*$)([\s\S]*?)(?=^\s*##\s+|\s*$)/m;
  const sectionMatch = md.match(sectionRe);
  if (!sectionMatch) return null;

  const sectionBody = sectionMatch[2];

  // Find first ```mermaid block within that section
  const mermaidRe = /```mermaid\s*\n([\s\S]*?)\n```/m;
  const mermaidMatch = sectionBody.match(mermaidRe);
  if (!mermaidMatch) return null;

  return {
    sectionStartIndex: sectionMatch.index,
    sectionHeader: sectionMatch[1],
    sectionBody,
    mermaidBody: mermaidMatch[1].trimEnd(),
  };
}

const arch = extractArchitectureMermaid(readme);

if (!arch) {
  console.log('No Mermaid block found under "## Architecture". Nothing to do.');
  process.exit(0);
}

const docsDir = path.join(repoRoot, "docs");
fs.mkdirSync(docsDir, { recursive: true });

const mmdFile = path.join(docsDir, "architecture.mmd");
const svgFile = path.join(docsDir, "architecture.svg");

fs.writeFileSync(mmdFile, arch.mermaidBody + "\n", "utf8");

// Render using mermaid-cli (mmdc)
run("mmdc", ["-i", mmdFile, "-o", svgFile, "-b", "transparent"]);

console.log("Rendered docs/architecture.svg");

// Use a raw GitHub URL so PyPI can render the image
const imgUrl = "https://raw.githubusercontent.com/marcostfermin/GeoFabric/main/docs/architecture.svg";

// Build replacement content for the Mermaid block inside Architecture section
const replacement =
  [
    "",
    "<!-- Rendered diagram (PyPI-friendly) -->",
    `<img src="${imgUrl}" alt="GeoFabric architecture diagram" width="900" />`,
    "",
    "<details>",
    "<summary>Mermaid source</summary>",
    "",
    "```mermaid",
    arch.mermaidBody.trimEnd(),
    "```",
    "",
    "</details>",
    ""
  ].join("\n");

// Now rewrite only the Mermaid block inside the Architecture section.
// We do this by rebuilding the Architecture section body with the replacement.
const sectionRe = /(^##\s+Architecture\s*$)([\s\S]*?)(?=^\s*##\s+|\s*$)/m;
const rewritten = readme.replace(sectionRe, (full, headerLine, body) => {
  const mermaidRe = /```mermaid\s*\n[\s\S]*?\n```/m;

  // If the section already contains the same imgUrl and details block, do nothing (idempotent).
  // This prevents churn commits.
  const alreadyHasImg = body.includes(imgUrl);
  const alreadyHasDetails = body.includes("<details>") && body.includes("Mermaid source");
  if (alreadyHasImg && alreadyHasDetails) return full;

  const newBody = body.replace(mermaidRe, replacement);
  return `${headerLine}${newBody}`;
});

if (rewritten !== readme) {
  fs.writeFileSync(readmePath, rewritten, "utf8");
  console.log('Updated README.md (Architecture section now uses rendered SVG and keeps Mermaid source).');
} else {
  console.log("README.md already up to date. No changes made.");
}
