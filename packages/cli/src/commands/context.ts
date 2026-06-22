import { buildContext, type EnforcementSummary } from "@research-copilot/core";
import { AI_TOOLS } from "@research-copilot/adapters";

export interface ContextArgs {
  repo: string;
  format: "text" | "json";
  now: string;
  eventName?: string;
  platform?: string;
}

export function enforcementForPlatform(platform = "claude-code"): EnforcementSummary {
  return AI_TOOLS[platform]?.enforcement ?? {
    platform,
    mode: "unavailable",
    reason: `unknown platform "${platform}"; enforcement capability cannot be determined`,
  };
}

export function runContext(args: ContextArgs): string {
  return buildContext(args.repo, {
    format: args.format,
    now: args.now,
    eventName: args.eventName,
    enforcement: enforcementForPlatform(args.platform),
  });
}
