export type InjectionClass = 1 | 2;
export interface ToolEntry {
  id: string; configDir: string; cliFlag: string;
  agentCapable: boolean; hasHooks: boolean;
  injectionClass: InjectionClass;
  agentFormat: "md" | "toml" | "none";
  skillsPaths: string[];
}
export const AI_TOOLS: Record<string, ToolEntry> = {
  "claude-code": {
    id: "claude-code", configDir: ".claude", cliFlag: "claude",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".claude/skills"],
  },
  codex: {
    id: "codex", configDir: ".codex", cliFlag: "codex",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "toml", skillsPaths: [".agents/skills"],
  },
};
