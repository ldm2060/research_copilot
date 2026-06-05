import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync, copyFileSync } from "node:fs";
import { join, basename } from "node:path";
import { stringify as stringifyYaml, parse as parseYaml } from "yaml";
import { parseSkillpacks } from "./parse-skillpacks.js";
import { resolveSkillpacks } from "./resolve-skillpacks.js";
import type { ResolvedSkillpack } from "./skillpacks.js";

/**
 * Lock file entry for a synced skillpack
 */
export interface SkillpackLockEntry {
  name: string;
  source: string;
  resolvedRef: string;
  syncedAt: string;
  agentCount: number;
  specCount: number;
}

export interface SkillpackLock {
  syncedAt: string;
  packs: SkillpackLockEntry[];
}

/**
 * Sync skillpacks from skillpacks.yaml to target directory
 *
 * @param repoRoot - Repository root (where skillpacks.yaml lives)
 * @param cacheDir - Cache directory for cloned packs
 * @param targetDir - Target directory to write agents/specs (e.g., research-kit/)
 * @returns Lock data recording what was synced
 */
export function syncSkillpacks(
  repoRoot: string,
  cacheDir: string,
  targetDir: string
): SkillpackLock {
  const yamlPath = join(repoRoot, "skillpacks.yaml");

  if (!existsSync(yamlPath)) {
    throw new Error(`skillpacks.yaml not found at ${yamlPath}`);
  }

  // Parse and resolve packs
  const manifest = parseSkillpacks(yamlPath);
  const enabledPacks = manifest.packs.filter(p => p.enabled !== false);

  if (enabledPacks.length === 0) {
    console.error("[sync] No enabled packs found in skillpacks.yaml");
    return { syncedAt: new Date().toISOString(), packs: [] };
  }

  const resolved = resolveSkillpacks(enabledPacks, cacheDir);

  // Prepare target directories
  const agentsDir = join(targetDir, "agents");
  const specsDir = join(targetDir, "specs");
  mkdirSync(agentsDir, { recursive: true });
  mkdirSync(specsDir, { recursive: true });

  // Copy files from each pack
  const lockEntries: SkillpackLockEntry[] = [];

  for (const pack of resolved) {
    let agentCount = 0;
    let specCount = 0;

    // Copy agents
    const packAgentsDir = join(pack.localPath, "agents");
    if (existsSync(packAgentsDir)) {
      const agents = readdirSync(packAgentsDir).filter(f => f.endsWith(".md"));
      for (const agent of agents) {
        const src = join(packAgentsDir, agent);
        const dest = join(agentsDir, agent);
        copyFileSync(src, dest);
        agentCount++;
      }
    }

    // Copy specs
    const packSpecsDir = join(pack.localPath, "specs");
    if (existsSync(packSpecsDir)) {
      const specs = readdirSync(packSpecsDir).filter(f => f.endsWith(".md"));
      for (const spec of specs) {
        const src = join(packSpecsDir, spec);
        const dest = join(specsDir, spec);
        copyFileSync(src, dest);
        specCount++;
      }
    }

    lockEntries.push({
      name: pack.name,
      source: pack.source,
      resolvedRef: pack.resolvedRef,
      syncedAt: new Date().toISOString(),
      agentCount,
      specCount
    });

    console.error(`[sync] ${pack.name}: ${agentCount} agents, ${specCount} specs`);
  }

  return {
    syncedAt: new Date().toISOString(),
    packs: lockEntries
  };
}

/**
 * Write skillpacks lock file
 *
 * @param lockPath - Path to skillpacks.lock.yaml
 * @param lock - Lock data
 */
export function writeLockFile(lockPath: string, lock: SkillpackLock): void {
  const yaml = stringifyYaml(lock);
  writeFileSync(lockPath, yaml, "utf-8");
}

/**
 * Read skillpacks lock file
 *
 * @param lockPath - Path to skillpacks.lock.yaml
 * @returns Lock data, or null if file doesn't exist
 */
export function readLockFile(lockPath: string): SkillpackLock | null {
  if (!existsSync(lockPath)) {
    return null;
  }

  const content = readFileSync(lockPath, "utf-8");
  return parseYaml(content) as SkillpackLock;
}
