import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, rmSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execSync } from "node:child_process";
import { sync } from "../src/commands/sync.js";

function createTestRepo(path: string, files: Record<string, string> = {}) {
  mkdirSync(path, { recursive: true });
  execSync("git init -b main", { cwd: path, stdio: "pipe" });
  execSync("git config user.email test@example.com", { cwd: path, stdio: "pipe" });
  execSync("git config user.name Test", { cwd: path, stdio: "pipe" });

  for (const [name, content] of Object.entries(files)) {
    const filePath = join(path, name);
    mkdirSync(join(filePath, ".."), { recursive: true });
    writeFileSync(filePath, content);
  }

  execSync("git add .", { cwd: path, stdio: "pipe" });
  execSync("git commit -m 'initial'", { cwd: path, stdio: "pipe" });
}

describe("sync command", () => {
  it("runs end-to-end", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const repoDir = join(tmp, "repo");
    const packDir = join(tmp, "pack");
    const cacheDir = join(tmp, "cache");
    const targetDir = join(tmp, "target");

    // Create pack
    createTestRepo(packDir, {
      "agents/test-agent.md": "# Test Agent\n",
      "specs/test-spec.md": "# Test Spec\n"
    });

    // Create repo with skillpacks.yaml
    mkdirSync(repoDir, { recursive: true });
    writeFileSync(join(repoDir, "skillpacks.yaml"), `
packs:
  - name: test-pack
    description: Test Pack
    source: ${packDir}
`);

    // Run sync
    sync({ repo: repoDir, cacheDir, targetDir });

    // Verify
    expect(existsSync(join(targetDir, "agents", "test-agent.md"))).toBe(true);
    expect(existsSync(join(targetDir, "specs", "test-spec.md"))).toBe(true);
    expect(existsSync(join(repoDir, "skillpacks.lock.yaml"))).toBe(true);

    const lockContent = readFileSync(join(repoDir, "skillpacks.lock.yaml"), "utf-8");
    expect(lockContent).toContain("test-pack");
    expect(lockContent).toContain("agentCount: 1");
    expect(lockContent).toContain("specCount: 1");

    rmSync(tmp, { recursive: true, force: true });
  });
});

