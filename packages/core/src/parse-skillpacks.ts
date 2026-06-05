import { readFileSync } from "node:fs";
import { parse as parseYaml } from "yaml";
import { SkillpacksYaml } from "./skillpacks.js";

/**
 * Parse skillpacks.yaml file
 *
 * @param path - Path to skillpacks.yaml
 * @returns Parsed skillpacks manifest
 * @throws If file doesn't exist or YAML is invalid
 */
export function parseSkillpacks(path: string): SkillpacksYaml {
  const content = readFileSync(path, "utf-8");
  const data = parseYaml(content);

  // Basic validation
  if (!data || typeof data !== "object") {
    throw new Error("skillpacks.yaml must be an object");
  }

  if (!Array.isArray((data as any).packs)) {
    throw new Error("skillpacks.yaml must have 'packs' array");
  }

  // Validate each pack has required fields
  for (const pack of (data as any).packs) {
    if (!pack.name || typeof pack.name !== "string") {
      throw new Error("Each pack must have a 'name' string");
    }
    if (!pack.source || typeof pack.source !== "string") {
      throw new Error(`Pack '${pack.name}' must have a 'source' URL`);
    }
  }

  return data as SkillpacksYaml;
}
