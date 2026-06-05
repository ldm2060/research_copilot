import { configureClaudeCode } from "./configurators/claude-code.js";
import { configureCodex } from "./configurators/codex.js";
import { configureOpenCode } from "./configurators/opencode.js";
import { configureGemini } from "./configurators/gemini.js";
import { configureCursor } from "./configurators/cursor.js";

export const CONFIGURATORS: Record<string, (repo: string) => void> = {
  "claude-code": configureClaudeCode,
  codex: configureCodex,
  opencode: configureOpenCode,
  gemini: configureGemini,
  cursor: configureCursor,
};

export function configurePlatform(repo: string, id: string): void {
  const fn = CONFIGURATORS[id];
  if (!fn) throw new Error(`unknown platform: ${id}`);
  fn(repo);
}
