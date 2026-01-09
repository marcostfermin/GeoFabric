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

const docsDir = path.join(repoRoot, "docs");
fs.mkdirSync(docsDir, { recursive: true });

const mmdFile = path.join(docsDir, "architecture.mmd");
const svgFile = path.join(docsDir, "architecture.svg");

if (!fs.existsSync(mmdFile)) {
  die("docs/architecture.mmd not found. Create it with your Mermaid diagram source.");
}

const puppeteerConfig = path.join(repoRoot, "scripts", "puppeteer.json");
if (!fs.existsSync(puppeteerConfig)) {
  die("scripts/puppeteer.json not found. Create it to disable Chromium sandbox in CI.");
}

run("mmdc", [
  "-i", mmdFile,
  "-o", svgFile,
  "-b", "transparent",
  "--puppeteerConfigFile", puppeteerConfig
]);

console.log("Rendered docs/architecture.svg (generated during docs build; not committed).");
