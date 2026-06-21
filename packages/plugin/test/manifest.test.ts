import { describe, expect, it } from "vitest";
import { execSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.resolve(__dirname, "..");

function pnpmCommand(): string {
  return process.platform === "win32" ? "pnpm.cmd" : "pnpm";
}

describe("plugin build manifests", () => {
  it("generates Claude Code manifest author metadata as an object", () => {
    execSync(`${pnpmCommand()} --dir "${pluginRoot}" build`, { stdio: "pipe" });

    const manifestPath = path.join(pluginRoot, "dist", ".claude-plugin", "plugin.json");
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));

    expect(manifest.author).toEqual({ name: "ldm2060" });
  });
});
