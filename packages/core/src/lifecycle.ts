import type { Status } from "./types.js";

export const TRANSITIONS: Record<Status, Status[]> = {
  planning: ["in_progress"],
  in_progress: ["verify"],
  verify: ["in_progress", "completed"],
  completed: [],
};

export function nextStatuses(from: Status): Status[] {
  return TRANSITIONS[from];
}
export function canTransition(from: Status, to: Status): boolean {
  return TRANSITIONS[from].includes(to);
}
export function assertTransition(from: Status, to: Status): void {
  if (!canTransition(from, to)) {
    throw new Error(`illegal transition: ${from} -> ${to} (allowed: ${TRANSITIONS[from].join(", ") || "none"})`);
  }
}
