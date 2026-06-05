import { buildContext } from "@research-copilot/core";

export interface ContextArgs { repo: string; format: "text" | "json"; now: string; eventName?: string; }
export function runContext(args: ContextArgs): string {
  return buildContext(args.repo, { format: args.format, now: args.now, eventName: args.eventName });
}
