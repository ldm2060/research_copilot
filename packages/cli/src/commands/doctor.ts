import * as fs from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { kitRoot, MCP_SERVERS } from "@research-copilot/adapters";
import { runInit } from "./init.js";
import {
  checkClaudePluginLoading,
  getInstalledPluginVersion,
  PLUGIN_PACKAGE,
  readCliVersion,
  type CommandRunner,
} from "./plugin.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

export interface DoctorOptions {
  strictPlugin?: boolean;
  fix?: boolean;
  skipPlugin?: boolean;
  runner?: CommandRunner;
}

interface Check {
  level: "OK" | "FAIL" | "WARN" | "INFO";
  message: string;
}

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

function checkPlugin(options: DoctorOptions): Check[] {
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

  const claude = checkClaudePluginLoading(options.runner);
  checks.push({ level: "INFO", message: claude.message });
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

  const checks = [...checkCoreConfig(repo), ...checkPlugin(options)];
  let ok = true;
  for (const check of checks) {
    report.push(`${check.level} ${check.message}`);
    if (check.level === "FAIL") ok = false;
  }

  return { ok, report };
}
