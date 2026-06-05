import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, rmSync, existsSync, mkdirSync, readdirSync, readFileSync, cpSync } from "node:fs";
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

describe("skillpacks integration - research-kit", () => {
  it("syncs research-kit pack with 10 agents", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const repoDir = join(tmp, "repo");
    const packDir = join(tmp, "research-kit");
    const cacheDir = join(tmp, "cache");
    const targetDir = join(tmp, "synced");

    // Copy real research-kit to temp location and make it a git repo
    const realResearchKitPath = join(process.cwd(), "research-kit");
    cpSync(realResearchKitPath, packDir, { recursive: true });

    // Initialize as git repo
    execSync("git init -b main", { cwd: packDir, stdio: "pipe" });
    execSync("git config user.email test@example.com", { cwd: packDir, stdio: "pipe" });
    execSync("git config user.name Test", { cwd: packDir, stdio: "pipe" });
    execSync("git add .", { cwd: packDir, stdio: "pipe" });
    execSync('git commit -m "research-kit pack"', { cwd: packDir, stdio: "pipe" });

    // Create repo directory
    mkdirSync(repoDir, { recursive: true });

    // Create skillpacks.yaml
    writeFileSync(
      join(repoDir, "skillpacks.yaml"),
      `packs:
  - name: research-kit
    description: Core research agents
    source: ${packDir}
    enabled: true
`
    );

    // Run sync
    sync({ repo: repoDir, cacheDir, targetDir });

    // Verify agents directory exists and has files
    const agentsDir = join(targetDir, "agents");
    expect(existsSync(agentsDir)).toBe(true);

    const agentFiles = readdirSync(agentsDir).filter((f) => f.endsWith(".md"));
    expect(agentFiles.length).toBeGreaterThanOrEqual(10);

    // Verify specific agent files exist
    const expectedAgents = [
      "rc-ideation.md",
      "rc-literature.md",
      "rc-experiment.md",
      "rc-writer.md",
      "rc-reviewer.md",
      "rc-rebuttal.md",
      "rc-polisher.md",
      "rc-plan.md",
      "rc-verify.md",
      "rc-update-spec.md",
    ];

    for (const agent of expectedAgents) {
      expect(existsSync(join(agentsDir, agent))).toBe(true);
    }

    // Verify lock file exists and has correct counts
    const lockPath = join(repoDir, "skillpacks.lock.yaml");
    expect(existsSync(lockPath)).toBe(true);

    const lockContent = readFileSync(lockPath, "utf-8");
    expect(lockContent).toContain("research-kit");
    expect(lockContent).toContain("agentCount: 10");

    rmSync(tmp, { recursive: true, force: true });
  });
});
