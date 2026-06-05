import { homedir } from "node:os";
import { join } from "node:path";
import { syncSkillpacks, writeLockFile } from "@research-copilot/core";

export interface SyncArgs {
  repo: string;
  cacheDir?: string;
  targetDir?: string;
}

/**
 * rc sync - Fetch skillpacks and render agents/specs
 */
export function sync(args: SyncArgs): void {
  const repoRoot = args.repo;
  const cacheDir = args.cacheDir || join(homedir(), ".cache", "research-copilot", "skillpacks");
  const targetDir = args.targetDir || join(repoRoot, "research-kit");

  console.error(`[sync] Repository: ${repoRoot}`);
  console.error(`[sync] Cache: ${cacheDir}`);
  console.error(`[sync] Target: ${targetDir}`);
  console.error("");

  const lock = syncSkillpacks(repoRoot, cacheDir, targetDir);

  const lockPath = join(repoRoot, "skillpacks.lock.yaml");
  writeLockFile(lockPath, lock);

  console.error("");
  console.error(`[sync] Lock file written: ${lockPath}`);
  console.error(`[sync] Synced ${lock.packs.length} packs with ${lock.packs.reduce((sum, p) => sum + p.agentCount, 0)} agents and ${lock.packs.reduce((sum, p) => sum + p.specCount, 0)} specs`);
}
