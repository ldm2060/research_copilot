import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, rmSync, readFileSync, existsSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execSync } from "node:child_process";
import { syncSkillpacks, writeLockFile, readLockFile } from "../src/sync-skillpacks.js";

// Helper: create a minimal git repo for testing
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

describe("syncSkillpacks", () => {
  it("syncs agents and specs from packs", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const repoDir = join(tmp, "repo");
    const pack1Dir = join(tmp, "pack1");
    const pack2Dir = join(tmp, "pack2");
    const cacheDir = join(tmp, "cache");
    const targetDir = join(tmp, "target");

    // Create pack repositories
    createTestRepo(pack1Dir, {
      "agents/agent1.md": "# Agent 1\n",
      "specs/spec1.md": "# Spec 1\n"
    });

    createTestRepo(pack2Dir, {
      "agents/agent2.md": "# Agent 2\n"
    });

    // Create repo with skillpacks.yaml
    mkdirSync(repoDir, { recursive: true });
    writeFileSync(join(repoDir, "skillpacks.yaml"), `
packs:
  - name: pack1
    description: Pack 1
    source: ${pack1Dir}
    enabled: true
  - name: pack2
    description: Pack 2
    source: ${pack2Dir}
    enabled: true
`);

    const lock = syncSkillpacks(repoDir, cacheDir, targetDir);

    // Verify files copied
    expect(existsSync(join(targetDir, "agents", "agent1.md"))).toBe(true);
    expect(existsSync(join(targetDir, "agents", "agent2.md"))).toBe(true);
    expect(existsSync(join(targetDir, "specs", "spec1.md"))).toBe(true);

    // Verify lock data
    expect(lock.packs.length).toBe(2);
    expect(lock.packs[0].name).toBe("pack1");
    expect(lock.packs[0].agentCount).toBe(1);
    expect(lock.packs[0].specCount).toBe(1);
    expect(lock.packs[1].name).toBe("pack2");
    expect(lock.packs[1].agentCount).toBe(1);
    expect(lock.packs[1].specCount).toBe(0);

    rmSync(tmp, { recursive: true, force: true });
  });

  it("skips disabled packs", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const repoDir = join(tmp, "repo");
    const pack1Dir = join(tmp, "pack1");
    const pack2Dir = join(tmp, "pack2");
    const cacheDir = join(tmp, "cache");
    const targetDir = join(tmp, "target");

    createTestRepo(pack1Dir, { "agents/agent1.md": "# Agent 1\n" });
    createTestRepo(pack2Dir, { "agents/agent2.md": "# Agent 2\n" });

    mkdirSync(repoDir, { recursive: true });
    writeFileSync(join(repoDir, "skillpacks.yaml"), `
packs:
  - name: pack1
    description: Pack 1
    source: ${pack1Dir}
    enabled: true
  - name: pack2
    description: Pack 2
    source: ${pack2Dir}
    enabled: false
`);

    const lock = syncSkillpacks(repoDir, cacheDir, targetDir);

    expect(existsSync(join(targetDir, "agents", "agent1.md"))).toBe(true);
    expect(existsSync(join(targetDir, "agents", "agent2.md"))).toBe(false);
    expect(lock.packs.length).toBe(1);
    expect(lock.packs[0].name).toBe("pack1");

    rmSync(tmp, { recursive: true, force: true });
  });
});

describe("lock file I/O", () => {
  it("writes and reads lock file", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const lockPath = join(tmp, "skillpacks.lock.yaml");

    const lock = {
      syncedAt: "2026-06-06T12:00:00Z",
      packs: [
        {
          name: "test-pack",
          source: "https://example.com/pack.git",
          resolvedRef: "abc123",
          syncedAt: "2026-06-06T12:00:00Z",
          agentCount: 5,
          specCount: 3
        }
      ]
    };

    writeLockFile(lockPath, lock);
    expect(existsSync(lockPath)).toBe(true);

    const read = readLockFile(lockPath);
    expect(read).toEqual(lock);

    rmSync(tmp, { recursive: true, force: true });
  });

  it("returns null for missing file", () => {
    const result = readLockFile("/nonexistent/path/lock.yaml");
    expect(result).toBe(null);
  });
});

