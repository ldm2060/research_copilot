import { execSync } from "node:child_process";
import { existsSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import type { SkillpackManifest, ResolvedSkillpack } from "./skillpacks.js";

/**
 * Resolve and fetch skillpacks to local cache
 *
 * @param packs - List of pack manifests from skillpacks.yaml
 * @param cacheDir - Directory to store cached packs (e.g., ~/.cache/research-copilot/skillpacks)
 * @returns List of resolved packs with local paths
 */
export function resolveSkillpacks(
  packs: SkillpackManifest[],
  cacheDir: string
): ResolvedSkillpack[] {
  // Ensure cache directory exists
  mkdirSync(cacheDir, { recursive: true });

  const resolved: ResolvedSkillpack[] = [];

  for (const pack of packs) {
    const packDir = join(cacheDir, pack.name);

    // Clone or update pack
    if (!existsSync(packDir)) {
      console.error(`[skillpacks] Cloning ${pack.name} from ${pack.source}...`);
      execSync(`git clone "${pack.source}" "${packDir}"`, {
        stdio: "inherit",
        encoding: "utf-8"
      });
    } else {
      console.error(`[skillpacks] Updating ${pack.name}...`);
      execSync(`git fetch origin`, {
        cwd: packDir,
        stdio: "inherit",
        encoding: "utf-8"
      });
    }

    // Checkout requested version (tag/branch) or default to latest main
    const ref = pack.version || "main";
    try {
      execSync(`git checkout "${ref}"`, {
        cwd: packDir,
        stdio: "pipe",
        encoding: "utf-8"
      });
      // If no version is specified, pull latest changes
      if (!pack.version) {
        execSync(`git pull origin "${ref}"`, {
          cwd: packDir,
          stdio: "pipe",
          encoding: "utf-8"
        });
      }
    } catch (err) {
      throw new Error(`Failed to checkout ${ref} for pack ${pack.name}: ${err}`);
    }

    // Get resolved commit SHA
    const resolvedRef = execSync("git rev-parse HEAD", {
      cwd: packDir,
      encoding: "utf-8"
    }).trim();

    resolved.push({
      ...pack,
      localPath: packDir,
      resolvedRef
    });
  }

  return resolved;
}

/**
 * Remove cached skillpack
 *
 * @param packName - Name of pack to remove
 * @param cacheDir - Cache directory
 */
export function removeSkillpack(packName: string, cacheDir: string): void {
  const packDir = join(cacheDir, packName);
  if (existsSync(packDir)) {
    rmSync(packDir, { recursive: true, force: true });
  }
}
