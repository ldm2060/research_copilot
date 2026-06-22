import * as fs from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { kitRoot, MCP_SERVERS, AI_TOOLS } from "@research-copilot/adapters";
import { runInit } from "./init.js";
import {
  checkClaudePluginLoading,
  getInstalledPluginVersion,
  PLUGIN_PACKAGE,
  readCliVersion,
  type CommandRunner,
} from "./plugin.js";
import { statusPluginRegistration } from "./plugin-register.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

export interface DoctorOptions {
  strictPlugin?: boolean;
  fix?: boolean;
  skipPlugin?: boolean;
  runner?: CommandRunner;
  platform?: string;
}

interface Check {
  level: "OK" | "FAIL" | "WARN" | "INFO";
  message: string;
}

const CLAUDE_PROJECT_PLUGIN_INSTALLED_MESSAGE = "Claude project plugin registration exists";
const CLAUDE_PLUGIN_LIST_MISSING_WITH_REGISTRATION_MESSAGE = "Claude Code is available but does not list project-registered research-copilot plugin; project plugin registration is installed";
const CLAUDE_PLUGIN_LIST_UNAVAILABLE_WITH_REGISTRATION_MESSAGE = "Claude Code plugin list unavailable; project plugin registration is installed";

function existsCheck(path: string, label: string): Check {
  return fs.existsSync(path)
    ? { level: "OK", message: `${label} exists` }
    : { level: "FAIL", message: `${label} exists` };
}

function readJson(path: string): any | null {
  try {
    return JSON.parse(fs.readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function expectedAgentNames(): string[] {
  const agentsDir = join(kitRoot(__dirname), "agents");
  return fs.readdirSync(agentsDir).filter(f => f.endsWith(".md")).sort();
}

function checkCoreConfig(repo: string): Check[] {
  const checks: Check[] = [];
  checks.push(existsCheck(join(repo, ".research"), ".research/"));
  checks.push(existsCheck(join(repo, ".research/workflow.md"), "workflow.md"));
  checks.push(existsCheck(join(repo, ".research/config.yaml"), ".research/config.yaml"));
  checks.push(existsCheck(join(repo, ".claude/settings.json"), ".claude/settings.json"));

  const settings = readJson(join(repo, ".claude/settings.json"));
  const rcHook = Array.isArray(settings?.hooks?.UserPromptSubmit)
    && settings.hooks.UserPromptSubmit.some((group: any) =>
      (group?.hooks ?? []).some((hook: any) => typeof hook?.command === "string" && hook.command.includes("rc context")));
  checks.push(rcHook
    ? { level: "OK", message: "Claude UserPromptSubmit hook contains rc context" }
    : { level: "FAIL", message: "Claude UserPromptSubmit hook contains rc context" });

  const agentDir = join(repo, ".claude/agents");
  for (const agent of expectedAgentNames()) {
    checks.push(fs.existsSync(join(agentDir, agent))
      ? { level: "OK", message: `.claude/agents/${agent} exists` }
      : { level: "FAIL", message: `.claude/agents/${agent} exists` });
  }

  const mcp = readJson(join(repo, ".mcp.json"));
  for (const name of Object.keys(MCP_SERVERS)) {
    checks.push(mcp?.mcpServers?.[name]
      ? { level: "OK", message: `.mcp.json includes ${name}` }
      : { level: "FAIL", message: `.mcp.json includes ${name}` });
  }

  const claudeMd = fs.existsSync(join(repo, "CLAUDE.md")) ? fs.readFileSync(join(repo, "CLAUDE.md"), "utf8") : "";
  checks.push(claudeMd.includes("Research workflow is governed by .research/")
    ? { level: "OK", message: "CLAUDE.md contains Research Copilot workflow instruction" }
    : { level: "FAIL", message: "CLAUDE.md contains Research Copilot workflow instruction" });

  return checks;
}

function checkEnforcement(platform = "claude-code"): Check[] {
  const entry = AI_TOOLS[platform];
  if (!entry) {
    return [{
      level: "FAIL",
      message: `Research workflow enforcement: unavailable (${platform}) — unknown platform`,
    }];
  }
  const level: Check["level"] = entry.enforcement.mode === "hard" ? "OK" : "WARN";
  const checks: Check[] = [{
    level,
    message: `Research workflow enforcement: ${entry.enforcement.mode} (${entry.enforcement.platform}) — ${entry.enforcement.reason}`,
  }];
  if (entry.enforcement.mode !== "hard") {
    checks.push({
      level: "WARN",
      message: "Strict sub-agent-only execution cannot be guaranteed on this platform.",
    });
  }
  return checks;
}

function checkClaudeProjectPluginRegistration(repo: string): Check {
  const [registration] = statusPluginRegistration({
    repo,
    platform: "claude",
    scope: "project",
    source: "npm",
  });

  return registration?.status === "ok"
    ? { level: "OK", message: CLAUDE_PROJECT_PLUGIN_INSTALLED_MESSAGE }
    : { level: "INFO", message: registration?.message ?? "project plugin: MISSING .claude/skills/research-copilot" };
}

function checkPlugin(repo: string, options: DoctorOptions): Check[] {
  const checks: Check[] = [];
  if (options.skipPlugin) {
    checks.push({ level: "INFO", message: "Skipped plugin checks" });
    return checks;
  }

  const cliVersion = readCliVersion();
  const pluginVersion = getInstalledPluginVersion(options.runner);
  const failLevel = options.strictPlugin ? "FAIL" : "WARN";

  if (!pluginVersion) {
    checks.push({
      level: failLevel,
      message: `Plugin not installed (run: npm install -g ${PLUGIN_PACKAGE}@${cliVersion})`,
    });
  } else if (pluginVersion !== cliVersion) {
    checks.push({
      level: failLevel,
      message: `Plugin version mismatch (CLI: ${cliVersion}, Plugin: ${pluginVersion}). Run: npm install -g ${PLUGIN_PACKAGE}@${cliVersion}`,
    });
  } else {
    checks.push({ level: "OK", message: `Plugin version matches (${cliVersion})` });
  }

  const registration = checkClaudeProjectPluginRegistration(repo);
  checks.push(registration);

  const claude = checkClaudePluginLoading(options.runner);
  const registered = registration.level === "OK";
  checks.push({
    level: "INFO",
    message: registered && claude.available && !claude.listed
      ? CLAUDE_PLUGIN_LIST_MISSING_WITH_REGISTRATION_MESSAGE
      : registered && !claude.available
        ? CLAUDE_PLUGIN_LIST_UNAVAILABLE_WITH_REGISTRATION_MESSAGE
        : claude.message,
  });
  return checks;
}

export function runDoctor(repo: string, options: DoctorOptions = {}): { ok: boolean; report: string[] } {
  const report: string[] = [];

  if (options.fix) {
    runInit({
      repo,
      platforms: ["claude-code"],
      user: "doctor-fix",
      skipPlugin: options.skipPlugin,
      strictPlugin: options.strictPlugin,
      runner: options.runner,
    });
    report.push("Fixed: reconciled Research Copilot project configuration");
  }

  const checks = [...checkCoreConfig(repo), ...checkEnforcement(options.platform), ...checkPlugin(repo, options)];
  let ok = true;
  for (const check of checks) {
    report.push(`${check.level} ${check.message}`);
    if (check.level === "FAIL") ok = false;
  }

  return { ok, report };
}
