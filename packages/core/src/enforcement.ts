import type { Kind, TaskRecord } from "./types.js";

export const RESEARCH_EXECUTORS = [
  "rc-plan",
  "rc-literature",
  "rc-ideation",
  "rc-experiment",
  "rc-writer",
  "rc-polisher",
  "rc-reviewer",
  "rc-rebuttal",
  "rc-verify",
  "rc-update-spec",
] as const;

export type ResearchExecutor = (typeof RESEARCH_EXECUTORS)[number];
export type EnforcementMode = "hard" | "soft" | "unavailable";

export interface EnforcementSummary {
  platform: string;
  mode: EnforcementMode;
  reason: string;
}

export type ArtifactOwner = "conductor" | ResearchExecutor | "kind-executor" | "non-research";

export interface ArtifactClaim {
  owner: ArtifactOwner;
  allowedExecutors: readonly ResearchExecutor[];
  reason: string;
}

const KIND_EXECUTOR: Record<Kind, ResearchExecutor> = {
  literature: "rc-literature",
  ideation: "rc-ideation",
  experiment: "rc-experiment",
  writing: "rc-writer",
  polish: "rc-polisher",
  review: "rc-reviewer",
  rebuttal: "rc-rebuttal",
};

const KIND_EXECUTORS: readonly ResearchExecutor[] = Object.values(KIND_EXECUTOR);

export function expectedExecutorFor(task: Pick<TaskRecord, "kind" | "status">): ResearchExecutor {
  if (task.status === "planning") return "rc-plan";
  if (task.status === "verify") return "rc-verify";
  if (task.status === "completed") return "rc-update-spec";
  return KIND_EXECUTOR[task.kind];
}

export function canExecutorClaim(task: Pick<TaskRecord, "kind" | "status">, executor: string): boolean {
  return expectedExecutorFor(task) === executor;
}

export function isResearchExecutor(executor: string): executor is ResearchExecutor {
  return (RESEARCH_EXECUTORS as readonly string[]).includes(executor);
}

function norm(filePath: string): string {
  return filePath.replace(/\\/g, "/").replace(/^\.\//, "");
}

function endsWithSegment(filePath: string, suffix: string): boolean {
  const p = norm(filePath);
  return p === suffix || p.endsWith(`/${suffix}`);
}

function underSegment(filePath: string, segment: string): boolean {
  return norm(filePath).split("/").includes(segment);
}

function claim(owner: ArtifactOwner, allowedExecutors: readonly ResearchExecutor[], reason: string): ArtifactClaim {
  return { owner, allowedExecutors, reason };
}

export function classifyArtifact(filePath: string): ArtifactClaim {
  const p = norm(filePath);

  if (endsWithSegment(p, ".research/.runtime/active-task")) {
    return claim("conductor", [], "active task pointer is conductor lifecycle metadata");
  }
  if (/\.research\/tasks\/[^/]+\/task\.json$/.test(p)) {
    return claim("conductor", [], "task metadata is conductor lifecycle metadata");
  }
  if (/\.research\/tasks\/[^/]+\/(prd\.md|execute\.jsonl|verify\.jsonl)$/.test(p)) {
    return claim("rc-plan", ["rc-plan"], "planning artifacts are owned by rc-plan");
  }
  if (/\.research\/tasks\/[^/]+\/verify\//.test(p)) {
    return claim("rc-verify", ["rc-verify"], "verification artifacts are owned by rc-verify");
  }
  if (/\.research\/tasks\/[^/]+\/(artifacts|research)\//.test(p)) {
    return claim("kind-executor", KIND_EXECUTORS, "task leaf artifacts are owned by the active kind executor");
  }
  if (p.startsWith(".research/spec/")) {
    return claim("rc-update-spec", ["rc-update-spec"], "cross-task spec is owned by rc-update-spec");
  }

  if (endsWithSegment(p, ".copilot/literature.md")) {
    return claim("kind-executor", ["rc-literature"], "legacy literature artifact is literature-executor owned");
  }
  if (endsWithSegment(p, ".copilot/ideas.md")) {
    return claim("kind-executor", ["rc-ideation"], "legacy idea artifact is ideation-executor owned");
  }
  if (endsWithSegment(p, ".copilot/experiments.md")) {
    return claim("kind-executor", ["rc-experiment"], "legacy experiment artifact is experiment-executor owned");
  }
  if (p.includes(".copilot/reviews/")) {
    return claim("kind-executor", ["rc-reviewer"], "legacy review artifact is review-executor owned");
  }
  if (underSegment(p, "sections") && p.endsWith(".tex")) {
    return claim("kind-executor", ["rc-writer", "rc-polisher", "rc-rebuttal"], "paper sections are writing, polish, or rebuttal executor owned");
  }
  if (endsWithSegment(p, "references.bib")) {
    return claim("kind-executor", ["rc-literature", "rc-writer"], "bibliography is literature or writing executor owned");
  }

  return claim("non-research", [], "path is outside research workflow ownership");
}

export function canWriteArtifact(
  actor: "conductor" | ResearchExecutor,
  task: Pick<TaskRecord, "kind" | "status">,
  filePath: string,
): boolean {
  const artifact = classifyArtifact(filePath);
  if (artifact.owner === "non-research") return true;
  if (actor === "conductor") return artifact.owner === "conductor";

  const expected = expectedExecutorFor(task);
  if (actor !== expected) return false;
  if (artifact.owner === "kind-executor") return artifact.allowedExecutors.includes(actor);
  return artifact.owner === actor;
}
