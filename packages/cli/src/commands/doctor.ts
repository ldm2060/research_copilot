import * as fs from "node:fs";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

function checkPluginVersion(): { ok: boolean; message: string } {
  try {
    // Get CLI version from package.json
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);
    // dist/rc.js -> dist/ -> packages/cli/ -> package.json
    const cliPackageJsonPath = join(__dirname, "../package.json");
    const cliPackageJson = JSON.parse(fs.readFileSync(cliPackageJsonPath, "utf-8"));
    const cliVersion = cliPackageJson.version;

    if (!cliVersion) {
      return {
        ok: false,
        message: "Unable to determine CLI version from package.json",
      };
    }

    // Get plugin version from npm list
    let pluginVersion: string | null = null;
    try {
      const output = execSync("npm list -g @research-copilot/plugin --json", {
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
        timeout: 5000,
      });
      const parsed = JSON.parse(output);
      // Navigate through the dependencies tree
      if (parsed.dependencies && parsed.dependencies["@research-copilot/plugin"]) {
        pluginVersion = parsed.dependencies["@research-copilot/plugin"].version;
      }
    } catch (err) {
      // Plugin not installed or npm list failed
      return {
        ok: false,
        message: "Plugin not installed (run: rc init)",
      };
    }

    if (!pluginVersion) {
      return {
        ok: false,
        message: "Plugin not installed (run: rc init)",
      };
    }

    // Compare versions
    if (pluginVersion !== cliVersion) {
      return {
        ok: false,
        message: `Plugin version mismatch (CLI: ${cliVersion}, Plugin: ${pluginVersion})`,
      };
    }

    return {
      ok: true,
      message: `Plugin version matches (${cliVersion})`,
    };
  } catch (err) {
    return {
      ok: false,
      message: `Plugin check failed: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

export function runDoctor(repo: string): { ok: boolean; report: string[] } {
  const report: string[] = [];
  let ok = true;
  const checks: [string, boolean][] = [
    [".research/ exists", fs.existsSync(join(repo, ".research"))],
    ["workflow.md exists", fs.existsSync(join(repo, ".research/workflow.md"))],
    [".claude/settings.json exists", fs.existsSync(join(repo, ".claude/settings.json"))],
  ];
  for (const [name, pass] of checks) {
    report.push(`${pass ? "OK " : "FAIL"} ${name}`);
    if (!pass) ok = false;
  }

  // Plugin version check (WARN only, doesn't fail overall status)
  const pluginCheck = checkPluginVersion();
  report.push(`${pluginCheck.ok ? "OK " : "WARN"} ${pluginCheck.message}`);

  return { ok, report };
}
