import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { researchPaths } from "@research-copilot/core";
import { configurePlatform, kitRoot } from "@research-copilot/adapters";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export interface ReconcileArgs {
  repo: string;
  platforms: string[];
  user: string;
}

export interface ReconcileResult {
  created: string[];
  updated: string[];
  skipped: string[];
}

function ensureDir(dir: string, rel: string, result: ReconcileResult): void {
  if (fs.existsSync(dir)) {
    result.skipped.push(rel);
    return;
  }
  fs.mkdirSync(dir, { recursive: true });
  result.created.push(rel);
}

function copyIfMissing(src: string, dst: string, rel: string, result: ReconcileResult): void {
  if (fs.existsSync(dst)) {
    result.skipped.push(rel);
    return;
  }
  fs.copyFileSync(src, dst);
  result.created.push(rel);
}

export function reconcileProject(args: ReconcileArgs): ReconcileResult {
  const result: ReconcileResult = { created: [], updated: [], skipped: [] };
  const paths = researchPaths(args.repo);

  for (const [dir, rel] of [
    [paths.tasks, ".research/tasks"],
    [paths.spec, ".research/spec"],
    [paths.workspace, ".research/workspace"],
    [paths.runtime, ".research/runtime"],
  ] as const) {
    ensureDir(dir, rel, result);
  }

  for (const name of ["venue", "writing", "baselines", "methodology", "novelty"]) {
    ensureDir(path.join(paths.spec, name), `.research/spec/${name}`, result);
  }

  const kit = kitRoot(__dirname);
  copyIfMissing(path.join(kit, "workflow.md"), paths.workflow, ".research/workflow.md", result);
  copyIfMissing(path.join(kit, "config.defaults.yaml"), paths.config, ".research/config.yaml", result);

  for (const platform of args.platforms) {
    configurePlatform(args.repo, platform);
    result.updated.push(`platform:${platform}`);
  }

  return result;
}
