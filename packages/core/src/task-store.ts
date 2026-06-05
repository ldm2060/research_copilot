import * as fs from "node:fs";
import * as path from "node:path";
import { researchPaths } from "./paths.js";
import type { TaskRecord, Kind, Priority } from "./types.js";

export function slugify(title: string): string {
  return title.toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
}

export interface CreateInput {
  title: string; kind: Kind; date: string;
  priority?: Priority; venue?: string; parent?: string; now?: string;
}

export function createTask(repo: string, input: CreateInput): TaskRecord {
  const id = `${input.date}-${slugify(input.title)}`;
  const now = input.now ?? input.date + "T00:00:00Z";
  const task: TaskRecord = {
    id, title: input.title, kind: input.kind, status: "planning",
    priority: input.priority ?? "P2", venue: input.venue, parent: input.parent,
    children: [], depends_on: [], gaps: [], created: now, updated: now,
  };
  writeTask(repo, task, now);
  return task;
}

export function taskJsonPath(repo: string, id: string): string {
  return path.join(researchPaths(repo).taskDir(id), "task.json");
}

export function writeTask(repo: string, task: TaskRecord, now?: string): void {
  if (now) task.updated = now;
  const dir = researchPaths(repo).taskDir(task.id);
  fs.mkdirSync(path.join(dir, "research"), { recursive: true });
  fs.mkdirSync(path.join(dir, "artifacts"), { recursive: true });
  fs.writeFileSync(taskJsonPath(repo, task.id), JSON.stringify(task, null, 2) + "\n", "utf8");
}

export function readTask(repo: string, id: string): TaskRecord {
  return JSON.parse(fs.readFileSync(taskJsonPath(repo, id), "utf8")) as TaskRecord;
}

export function listTasks(repo: string): TaskRecord[] {
  const dir = researchPaths(repo).tasks;
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter(id => fs.existsSync(taskJsonPath(repo, id)))
    .map(id => readTask(repo, id));
}
