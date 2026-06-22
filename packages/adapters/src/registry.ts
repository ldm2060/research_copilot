import type { EnforcementSummary } from "@research-copilot/core";

export type InjectionClass = 1 | 2;
export interface ToolEntry {
  id: string; configDir: string; cliFlag: string;
  agentCapable: boolean; hasHooks: boolean;
  injectionClass: InjectionClass;
  agentFormat: "md" | "toml" | "none";
  skillsPaths: string[];
  enforcement: EnforcementSummary;
}
export const AI_TOOLS: Record<string, ToolEntry> = {
  "claude-code": {
    id: "claude-code", configDir: ".claude", cliFlag: "claude",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".claude/skills"],
    enforcement: {
      platform: "claude-code",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    },
  },
  codex: {
    id: "codex", configDir: ".codex", cliFlag: "codex",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "toml", skillsPaths: [".agents/skills"],
    enforcement: {
      platform: "codex",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    },
  },
  opencode: {
    id: "opencode", configDir: ".opencode", cliFlag: "opencode",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".opencode/skills"],
    enforcement: {
      platform: "opencode",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    },
  },
  gemini: {
    id: "gemini", configDir: ".gemini", cliFlag: "gemini",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".gemini/skills", ".agents/skills"],
    enforcement: {
      platform: "gemini",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    },
  },
  cursor: {
    id: "cursor", configDir: ".cursor", cliFlag: "cursor",
    agentCapable: true, hasHooks: false, injectionClass: 2,
    agentFormat: "md", skillsPaths: [".cursor/skills"],
    enforcement: {
      platform: "cursor",
      mode: "soft",
      reason: "platform lacks hook-based hard deny; breadcrumb rules and agents are advisory",
    },
  },
  windsurf: {
    id: "windsurf", configDir: ".windsurf", cliFlag: "windsurf",
    agentCapable: false, hasHooks: false, injectionClass: 2,
    agentFormat: "none", skillsPaths: [".windsurf/workflows"],
    enforcement: {
      platform: "windsurf",
      mode: "soft",
      reason: "platform lacks hook-based hard deny and executable sub-agents; workflows are advisory",
    },
  },
};
