/**
 * Skillpack manifest schema
 *
 * A skillpack is a git repository containing:
 * - agents/*.md (agent definitions)
 * - specs/*.md (task specifications)
 * - meta.yaml (pack metadata)
 */

export interface SkillpackManifest {
  /** Pack identifier (kebab-case) */
  name: string;

  /** Human-readable description */
  description: string;

  /** Git repository URL */
  source: string;

  /** Version constraint (git tag/branch, semver-style) */
  version?: string;

  /** Whether this pack is enabled by default */
  enabled?: boolean;
}

export interface SkillpacksYaml {
  /** List of available skillpacks */
  packs: SkillpackManifest[];
}

/**
 * Resolved skillpack with local filesystem path
 */
export interface ResolvedSkillpack extends SkillpackManifest {
  /** Local cache path where pack is stored */
  localPath: string;

  /** Resolved git ref (commit SHA) */
  resolvedRef: string;
}
