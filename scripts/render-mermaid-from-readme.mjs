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

// Newline pattern that matches both LF and CRLF
const NL = "\\r?\\n";

function getArchitectureSection(md) {
  // (^## Architecture$)(...until next ## heading or EOF)
  const sectionRe = new RegExp("(^##\\s+Architecture\\s*$)([\\s\\S]*?)(?=^\\s*##\\s+|\\s*$)", "m");
  const m = md.match(sectionRe);
  if (!m) return null;
  return { header: m[1], body: m[2], fullMatch: m[0] };
}

function getFirstMermaidBlock(text) {
  const mermaidRe = new RegExp("```mermaid\\s*" + NL + "([\\s\\S]*?)" + NL + "```", "m");
  const m = text.match(mermaidRe);
  if (!m) return null;
  return m[1].trimEnd();
}

const arch = getArchitectureSection(readme);

if (!arch) {
  console.log('No "## Architecture" section found in README.md. Nothing to do.');
  process.exit(0);
}

const mermaidBody = getFirstMermaidBlock(arch.body);

if (!mermaidBody) {
  console.log('No Mermaid block found under "## Architecture". Nothing to do.');
  process.exit(0);
}

const docsDir = path.join(repoRoot, "docs");
fs.mkdirSync(docsDir, { recursive: true });

const mmdFile = path.join(docsDir, "architecture.mmd");
const svgFile = path.join(docsDir, "architecture.svg");

fs.writeFileSync(mmdFile, mermaidBody + "\n", "utf8");

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
    mermaidBody.trimEnd(),
    "```",
    "",
    "</details>",
    ""
  ].join("\n");

// Replace the first Mermaid block within the Architecture section
const mermaidBlockRe = new RegExp("```mermaid\\s*" + NL + "[\\s\\S]*?" + NL + "```", "m");

const alreadyRendered =
  arch.body.includes(imgUrl) &&
  arch.body.includes("<details>") &&
  arch.body.includes("Mermaid source");

if (!alreadyRendered) {
  const newArchBody = arch.body.replace(mermaidBlockRe, replacement);
  const rewritten = readme.replace(arch.fullMatch, `${arch.header}${newArchBody}`);

  if (rewritten !== readme) {
    fs.writeFileSync(readmePath, rewritten, "utf8");
    console.log("Updated README.md (Architecture now uses rendered SVG + keeps Mermaid source).");
  } else {
    console.log("README.md not modified (replacement did not apply).");
  }
} else {
  console.log("README.md already contains rendered diagram markup. No rewrite needed.");
}
