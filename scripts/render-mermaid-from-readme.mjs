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
function extractArchitectureMermaid(md) {
  const sectionRe = /(^##\s+Architecture\s*$)([\s\S]*?)(?=^\s*##\s+|\s*$)/m;
  const sectionMatch = md.match(sectionRe);
  if (!sectionMatch) return null;

  const sectionBody = sectionMatch[2];

  const mermaidRe = /```mermaid\s*\n([\s\S]*?)\n```/m;
  const mermaidMatch = sectionBody.match(mermaidRe);
  if (!mermaidMatch) return null;

  return {
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

// Raw GitHub URL so PyPI can render the image
const imgUrl = "https://raw.githubusercontent.com/marcostfermin/GeoFabric/main/docs/architecture.svg";

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

// Rewrite only the Mermaid block inside the Architecture section
const sectionRe = /(^##\s+Architecture\s*$)([\s\S]*?)(?=^\s*##\s+|\s*$)/m;
const rewritten = readme.replace(sectionRe, (full, headerLine, body) => {
  const mermaidRe = /```mermaid\s*\n[\s\S]*?\n```/m;

  // Idempotency: don't churn commits if already rendered
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
