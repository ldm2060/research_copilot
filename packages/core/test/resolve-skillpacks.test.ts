import { describe, it, expect } from "vitest";
import { mkdtempSync, rmSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execSync } from "node:child_process";
import { resolveSkillpacks, removeSkillpack } from "../src/resolve-skillpacks.js";
import type { SkillpackManifest } from "../src/skillpacks.js";

// Helper: create a minimal git repo for testing
function createTestRepo(path: string, files: Record<string, string> = {}) {
  mkdirSync(path, { recursive: true });
  execSync("git init -b main", { cwd: path, stdio: "pipe" });
  execSync("git config user.email test@example.com", { cwd: path, stdio: "pipe" });
  execSync("git config user.name Test", { cwd: path, stdio: "pipe" });

  // Write files
  for (const [name, content] of Object.entries(files)) {
    const filePath = join(path, name);
    const dir = join(filePath, "..");
    mkdirSync(dir, { recursive: true });
    writeFileSync(filePath, content);
  }

  execSync("git add .", { cwd: path, stdio: "pipe" });
  execSync("git commit -m 'initial'", { cwd: path, stdio: "pipe" });
}

describe("resolveSkillpacks", () => {
  it("clones and resolves pack", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const repoDir = join(tmp, "test-repo");
    const cacheDir = join(tmp, "cache");

    // Create test repo
    createTestRepo(repoDir, {
      "meta.yaml": "name: test-pack\n",
      "agents/test.md": "# Test Agent\n"
    });

    const packs: SkillpackManifest[] = [
      {
        name: "test-pack",
        description: "Test",
        source: repoDir
      }
    ];

    const resolved = resolveSkillpacks(packs, cacheDir);

    expect(resolved.length).toBe(1);
    expect(resolved[0].name).toBe("test-pack");
    expect(resolved[0].localPath).toBe(join(cacheDir, "test-pack"));
    expect(resolved[0].resolvedRef).toMatch(/^[0-9a-f]{40}$/);
    expect(existsSync(join(cacheDir, "test-pack", "meta.yaml"))).toBe(true);

    rmSync(tmp, { recursive: true, force: true });
  });

  it("updates existing clone", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const repoDir = join(tmp, "test-repo");
    const cacheDir = join(tmp, "cache");

    // Create test repo
    createTestRepo(repoDir, { "file1.txt": "v1" });

    const packs: SkillpackManifest[] = [
      { name: "test-pack", description: "Test", source: repoDir }
    ];

    // First resolve
    resolveSkillpacks(packs, cacheDir);

    // Add commit to source repo
    writeFileSync(join(repoDir, "file2.txt"), "v2");
    execSync("git add .", { cwd: repoDir, stdio: "pipe" });
    execSync("git commit -m 'v2'", { cwd: repoDir, stdio: "pipe" });

    // Second resolve should fetch updates
    const resolved = resolveSkillpacks(packs, cacheDir);

    expect(existsSync(join(cacheDir, "test-pack", "file2.txt"))).toBe(true);

    rmSync(tmp, { recursive: true, force: true });
  });
});

describe("removeSkillpack", () => {
  it("removes cached pack", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const cacheDir = join(tmp, "cache");
    const packDir = join(cacheDir, "test-pack");

    mkdirSync(packDir, { recursive: true });
    writeFileSync(join(packDir, "test.txt"), "content");

    removeSkillpack("test-pack", cacheDir);

    expect(existsSync(packDir)).toBe(false);

    rmSync(tmp, { recursive: true, force: true });
  });
});
