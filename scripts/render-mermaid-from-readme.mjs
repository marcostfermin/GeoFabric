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

// tolerant mermaid fence matcher (LF or CRLF, optional indent)
const MERMAID_BLOCK_RE = /(^|\r?\n)[ \t]*```mermaid[ \t]*\r?\n([\s\S]*?)\r?\n[ \t]*```/m;
const ARCH_HEADER_RE = /^##\s+Architecture\s*$/m;

function findMermaidAfterArchitecture(md) {
  const headerMatch = md.match(ARCH_HEADER_RE);
  if (!headerMatch) return null;

  const startIndex = headerMatch.index + headerMatch[0].length;
  const tail = md.slice(startIndex);

  const m = tail.match(MERMAID_BLOCK_RE);
  if (!m) return null;

  return m[2].trimEnd();
}

let mermaidBody = findMermaidAfterArchitecture(readme);
if (!mermaidBody) {
  // fallback: if section parsing fails, take first mermaid anywhere
  const m = readme.match(MERMAID_BLOCK_RE);
  if (!m) {
    console.log('No Mermaid block found in README.md. Nothing to do.');
    process.exit(0);
  }
  console.log('No Mermaid block found after "## Architecture". Using first Mermaid block in README.');
  mermaidBody = m[2].trimEnd();
} else {
  console.log('Found Mermaid block after "## Architecture".');
}

const docsDir = path.join(repoRoot, "docs");
fs.mkdirSync(docsDir, { recursive: true });

const mmdFile = path.join(docsDir, "architecture.mmd");
const svgFile = path.join(docsDir, "architecture.svg");

fs.writeFileSync(mmdFile, mermaidBody + "\n", "utf8");

// Puppeteer sandbox workaround for GitHub runners
const puppeteerConfig = path.join(repoRoot, "scripts", "puppeteer.json");
if (!fs.existsSync(puppeteerConfig)) die("scripts/puppeteer.json not found");

run("mmdc", [
  "-i", mmdFile,
  "-o", svgFile,
  "-b", "transparent",
  "--puppeteerConfigFile", puppeteerConfig
]);

console.log("Rendered docs/architecture.svg (not committed; used for docs build).");
