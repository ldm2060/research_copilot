import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { AI_TOOLS } from "@research-copilot/adapters";
import {
  PLUGIN_PACKAGE,
  defaultCommandRunner,
  readCliVersion,
  syncPluginPackage,
  type CommandRunner,
} from "./plugin.js";

export type PluginPlatformInput = "claude" | "claude-code" | "codex" | "gemini" | "cursor" | "opencode" | "windsurf" | "all" | "configured";
export type PluginScope = "project" | "user";
export type PluginSource = "npm" | "local";
export type PluginOperationStatus = "ok" | "missing" | "installed" | "updated" | "removed" | "skipped" | "failed";

export interface PluginRegistrationOptions {
  repo: string;
  platform: string;
  scope: PluginScope;
  source: PluginSource;
  sourcePath?: string;
  homeDir?: string;
  runner?: CommandRunner;
  cliVersion?: string;
}

export interface PluginRegistrationResult {
  platform: string;
  scope: PluginScope;
  target: string;
  status: PluginOperationStatus;
  message: string;
}

const VALID_PLATFORM_INPUTS = ["claude", "claude-code", "codex", "gemini", "cursor", "opencode", "windsurf", "all", "configured"];
const PLATFORM_ORDER = Object.keys(AI_TOOLS);
const RC_METADATA_FILES = [
  [".claude-plugin", "plugin.json"],
  [".codex-plugin", "plugin.toml"],
  [".gemini-plugin", "plugin.json"],
  [".cursor-plugin", "plugin.json"],
  [".opencode-plugin", "plugin.json"],
  [".windsurf-plugin", "plugin.json"],
];

export function normalizePluginPlatform(input: string): string {
  if (input === "claude") return "claude-code";
  if (input in AI_TOOLS) return input;
  throw new Error(`unknown platform: ${input}. Valid platforms: ${VALID_PLATFORM_INPUTS.join(", ")}`);
}

export function expandPluginPlatforms(repo: string, input: string): string[] {
  if (input === "all") return [...PLATFORM_ORDER];
  if (input === "configured") {
    const configured = PLATFORM_ORDER.filter(id => fs.existsSync(path.join(repo, AI_TOOLS[id].configDir)));
    return configured.length > 0 ? configured : ["claude-code"];
  }
  return [normalizePluginPlatform(input)];
}

function hasResearchCopilotMetadata(dir: string): boolean {
  return RC_METADATA_FILES.some(parts => {
    const file = path.join(dir, ...parts);
    if (!fs.existsSync(file)) return false;
    return fs.readFileSync(file, "utf8").includes("research-copilot");
  });
}

function hasPluginContentDir(dir: string): boolean {
  return ["skills", "agents", "hooks"].some(name => fs.existsSync(path.join(dir, name)));
}

function validatePluginDist(dir: string): void {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    throw new Error(`plugin source does not exist: ${dir}`);
  }
  if (!hasResearchCopilotMetadata(dir) || !hasPluginContentDir(dir)) {
    throw new Error(`${dir} does not look like @research-copilot/plugin dist`);
  }
}

export function resolvePluginSource(options: PluginRegistrationOptions): string {
  if (options.source === "local") {
    if (!options.sourcePath) throw new Error("--path is required when --source local is used");
    const resolved = path.resolve(options.repo, options.sourcePath);
    validatePluginDist(resolved);
    return resolved;
  }

  const runner = options.runner ?? defaultCommandRunner;
  const version = options.cliVersion ?? readCliVersion();
  const sync = syncPluginPackage({
    version,
    skip: false,
    strict: true,
    runner,
  });
  if (sync.status === "warning") throw new Error(sync.message);
  const npmRoot = runner.exec("npm root -g", { timeout: 5000 }).trim();
  if (!npmRoot) throw new Error(`Unable to resolve npm global root. Run: npm install -g ${PLUGIN_PACKAGE}@${version}`);
  const dist = path.join(npmRoot, "@research-copilot", "plugin", "dist");
  validatePluginDist(dist);
  return dist;
}

function projectTargetRoots(repo: string, platform: string): string[] {
  const entry = AI_TOOLS[platform];
  if (!entry) throw new Error(`unknown platform: ${platform}`);
  return entry.skillsPaths.map(rel => path.join(repo, rel));
}

export function resolvePlatformTargets(options: PluginRegistrationOptions & { platform: string }): string[] {
  const platform = normalizePluginPlatform(options.platform);
  if (options.scope === "user") {
    if (platform !== "claude-code") {
      throw new Error(`user scope is only supported for claude. ${platform} supports project scope only.`);
    }
    return [path.join(options.homeDir ?? os.homedir(), ".claude", "skills", "research-copilot")];
  }
  return projectTargetRoots(options.repo, platform).map(root => path.join(root, "research-copilot"));
}

function relativeToRepo(repo: string, target: string): string {
  const rel = path.relative(repo, target);
  return rel && !rel.startsWith("..") ? rel.replace(/\\/g, "/") : target;
}

function copyDir(src: string, dst: string): void {
  fs.cpSync(src, dst, { recursive: true });
}

function safeExistingTarget(target: string): "missing" | "research-copilot" | "foreign" {
  if (!fs.existsSync(target)) return "missing";
  return hasResearchCopilotMetadata(target) ? "research-copilot" : "foreign";
}

function resultsForTargets(options: PluginRegistrationOptions): Array<{ platform: string; target: string }> {
  return expandPluginPlatforms(options.repo, options.platform).flatMap(platform =>
    resolvePlatformTargets({ ...options, platform }).map(target => ({ platform, target })),
  );
}

export function installPluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[] {
  const source = resolvePluginSource(options);
  const results: PluginRegistrationResult[] = [];

  for (const item of resultsForTargets(options)) {
    const existing = safeExistingTarget(item.target);
    if (existing === "foreign") {
      results.push({
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "failed",
        message: `refusing to overwrite non-Research-Copilot directory: ${relativeToRepo(options.repo, item.target)}`,
      });
      continue;
    }

    fs.mkdirSync(path.dirname(item.target), { recursive: true });
    if (existing === "research-copilot") fs.rmSync(item.target, { recursive: true, force: true });
    copyDir(source, item.target);
    results.push({
      platform: item.platform,
      scope: options.scope,
      target: item.target,
      status: existing === "research-copilot" ? "updated" : "installed",
      message: `${existing === "research-copilot" ? "Updated" : "Installed"} research-copilot plugin at ${relativeToRepo(options.repo, item.target)}`,
    });
  }

  return results;
}

export function statusPluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[] {
  return resultsForTargets(options).map(item => {
    const existing = safeExistingTarget(item.target);
    if (existing === "research-copilot") {
      return {
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "ok",
        message: `project plugin: OK ${relativeToRepo(options.repo, item.target)}`,
      };
    }
    if (existing === "foreign") {
      return {
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "failed",
        message: `project plugin: BLOCKED ${relativeToRepo(options.repo, item.target)} is not Research Copilot-managed`,
      };
    }
    return {
      platform: item.platform,
      scope: options.scope,
      target: item.target,
      status: "missing",
      message: `project plugin: MISSING ${relativeToRepo(options.repo, item.target)}`,
    };
  });
}

export function removePluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[] {
  return resultsForTargets(options).map(item => {
    const existing = safeExistingTarget(item.target);
    if (existing === "missing") {
      return {
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "missing",
        message: `No research-copilot plugin registration at ${relativeToRepo(options.repo, item.target)}`,
      };
    }
    if (existing === "foreign") {
      return {
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "failed",
        message: `refusing to remove non-Research-Copilot directory: ${relativeToRepo(options.repo, item.target)}`,
      };
    }
    fs.rmSync(item.target, { recursive: true, force: true });
    return {
      platform: item.platform,
      scope: options.scope,
      target: item.target,
      status: "removed",
      message: `Removed research-copilot plugin registration at ${relativeToRepo(options.repo, item.target)}`,
    };
  });
}
