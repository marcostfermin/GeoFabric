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

// Match mermaid fence with:
// - optional indentation before ```mermaid
// - optional whitespace after "mermaid"
// - LF or CRLF line endings
const MERMAID_BLOCK_RE = /(^|\r?\n)[ \t]*```mermaid[ \t]*\r?\n([\s\S]*?)\r?\n[ \t]*```/m;

// Find "## Architecture" line (tolerant of trailing spaces / CRLF)
const ARCH_HEADER_RE = /^##\s+Architecture\s*$/m;

function findMermaidAfterArchitecture(md) {
  const headerMatch = md.match(ARCH_HEADER_RE);
  if (!headerMatch) return null;

  // Start searching after the header line
  const startIndex = headerMatch.index + headerMatch[0].length;
  const tail = md.slice(startIndex);

  const m = tail.match(MERMAID_BLOCK_RE);
  if (!m) return null;

  return m[2].trimEnd();
}

function findFirstMermaidAnywhere(md) {
  const m = md.match(MERMAID_BLOCK_RE);
  if (!m) return null;
  return m[2].trimEnd();
}

let mermaidBody = findMermaidAfterArchitecture(readme);

if (!mermaidBody) {
  // fallback: still render something if README has mermaid elsewhere
  mermaidBody = findFirstMermaidAnywhere(readme);
  if (!mermaidBody) {
    console.log("No Mermaid block found in README.md. Nothing to do.");
    process.exit(0);
  }
  console.log('No Mermaid block found after "## Architecture". Using first Mermaid block found in README.');
} else {
  console.log('Found Mermaid block after "## Architecture".');
}

const docsDir = path.join(repoRoot, "docs");
fs.mkdirSync(docsDir, { recursive: true });

const mmdFile = path.join(docsDir, "architecture.mmd");
const svgFile = path.join(docsDir, "architecture.svg");

fs.writeFileSync(mmdFile, mermaidBody + "\n", "utf8");

// Render using mermaid-cli (mmdc) with Puppeteer sandbox disabled
const puppeteerConfig = path.join(repoRoot, "scripts", "puppeteer.json");
run("mmdc", [
  "-i", mmdFile,
  "-o", svgFile,
  "-b", "transparent",
  "--puppeteerConfigFile", puppeteerConfig
]);

console.log("Rendered docs/architecture.svg");

// Optional README rewrite to PyPI-friendly image
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

function rewriteArchitectureSection(md) {
  const sectionRe = /(^##\s+Architecture\s*$)([\s\S]*?)(?=^\s*##\s+|\s*$)/m;
  const sm = md.match(sectionRe);
  if (!sm) return md;

  const header = sm[1];
  const body = sm[2];
  const full = sm[0];

  const alreadyRendered =
    body.includes(imgUrl) &&
    body.includes("<details>") &&
    body.includes("Mermaid source");

  if (alreadyRendered) return md;

  const hasMermaidInSection = MERMAID_BLOCK_RE.test(body);

  let newBody;
  if (hasMermaidInSection) {
    newBody = body.replace(MERMAID_BLOCK_RE, "\n" + replacement + "\n");
  } else {
    newBody = "\n" + replacement + "\n" + body;
  }

  return md.replace(full, `${header}${newBody}`);
}

const rewritten = rewriteArchitectureSection(readme);
if (rewritten !== readme) {
  fs.writeFileSync(readmePath, rewritten, "utf8");
  console.log("Updated README.md (Architecture section now uses rendered SVG + keeps Mermaid source).");
} else {
  console.log("README.md not modified.");
}
