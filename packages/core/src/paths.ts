import * as path from "node:path";

export interface ResearchPaths {
  root: string; tasks: string; spec: string; workspace: string; runtime: string;
  workflow: string; config: string; activeTask: string; graphIndex: string;
  taskDir(id: string): string;
}

export function researchPaths(repoRoot: string): ResearchPaths {
  const root = path.join(repoRoot, ".research");
  const runtime = path.join(root, ".runtime");
  return {
    root,
    tasks: path.join(root, "tasks"),
    spec: path.join(root, "spec"),
    workspace: path.join(root, "workspace"),
    runtime,
    workflow: path.join(root, "workflow.md"),
    config: path.join(root, "config.yaml"),
    activeTask: path.join(runtime, "active-task"),
    graphIndex: path.join(runtime, "graph-index.json"),
    taskDir: (id: string) => path.join(root, "tasks", id),
  };
}
