# Adding a platform

This is the milestone-2 onboarding doc: how to bring a new coding-agent platform under Research Copilot. The framework follows Trellis's registry pattern (spec §6.3), so a new platform is **one registry entry + one configurator + template differences** — no changes to `core`.

Read [architecture.md](architecture.md) first for the class-1/class-2 model and the role of `rc context`.

## Step 1 — add a registry entry (`packages/adapters/src/registry.ts`)

Every platform is one `ToolEntry` in the `AI_TOOLS` map. The Phase 0 entry (the only shipped one):

```ts
export interface ToolEntry {
  id: string;                  // stable platform key, e.g. "codex"
  configDir: string;           // where its config lives, e.g. ".codex"
  cliFlag: string;             // the rc init flag / cli name, e.g. "codex"
  agentCapable: boolean;       // can it host subagents?
  hasHooks: boolean;           // does it support per-turn hooks?
  injectionClass: 1 | 2;       // 1 = push/hook, 2 = pull/breadcrumb
  agentFormat: "md" | "toml" | "none";
  skillsPaths: string[];       // where rendered skills go
}

export const AI_TOOLS: Record<string, ToolEntry> = {
  "claude-code": {
    id: "claude-code", configDir: ".claude", cliFlag: "claude",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".claude/skills"],
  },
};
```

Add your platform alongside it. Use the spec §6.1 platform table as the source of truth for each field (config dir, agent format, injection class, MCP config path, skills path). For example, a Codex entry would be `injectionClass: 1`, `agentFormat: "toml"`, `configDir: ".codex"`; a Cursor entry would be `injectionClass: 2`, `agentFormat: "md"` (it also reads `.claude/agents/`).

## Step 2 — decide the injection class

This is the key design decision and it follows directly from whether the platform can push context every turn:

- **Class-1 (push / hook)** — the platform fires a per-turn event you can hook. Wire that hook to run `rc context --platform <id>` and feed stdout in as additional context. Mechanisms per platform:
  - Claude Code: `UserPromptSubmit` hook in `.claude/settings.json`.
  - Codex: `UserPromptSubmit` hook (requires `[features] hooks = true`; version-gated — fall back to a breadcrumb on old versions).
  - Gemini CLI: `BeforeAgent` hook in `.gemini/settings.json`.
  - OpenCode: an in-process plugin using `experimental.chat.system.transform` that calls `@research-copilot/core` directly (no shelling out).
- **Class-2 (pull / breadcrumb)** — the platform has no per-turn injection. Inject once at session start, then install an always-on rule that forces the agent to re-echo `Active task: <path>` every turn and re-resolve state via `rc task current`. Cursor (`.cursor/rules/*.mdc` with `alwaysApply`) and Windsurf (`always_on` rule; agent-less, so executors degrade to inline workflow) are class-2. The breadcrumb protocol is the spec §16.5 contract.

In all cases the produced context is identical — it comes from the single source of truth, `rc context`. The adapter is only "call it at the right moment and route its output in."

## Step 3 — write `configure<Platform>()` (`packages/adapters/src/configurators/<platform>.ts`)

Model it on the shipped Claude Code configurator (`configurators/claude-code.ts`). The pattern:

1. Locate the content kit with `kitRoot(__dirname)`.
2. **Wire injection idempotently.** Read any existing config, check whether our hook/rule is already present (the Claude Code configurator scans for a command containing `rc context`), and only then merge ours in with `deepMergeJson` so foreign config is preserved.
3. **Render agents.** Copy/transform the neutral `research-kit/agents/*.md` templates into the platform's format and directory (verbatim `.md` for Claude Code; `.toml` for Codex; skip for agent-less Windsurf).
4. **Append a behavioural note** to the platform's project memory file (e.g. `CLAUDE.md`), idempotently.

The Claude Code injection wiring, for reference:

```ts
const ours = {
  hooks: {
    UserPromptSubmit: [{
      matcher: "*",
      hooks: [{ type: "command", command: "rc context --inject --format text", timeout: 20 }],
    }],
  },
};
const merged = alreadyInjected ? existing : deepMergeJson(existing, ours);
fs.writeFileSync(settingsPath, JSON.stringify(merged, null, 2) + "\n", "utf8");
```

Export it from `packages/adapters/src/index.ts`, then call it from `rc init` when the corresponding flag (`--codex`, `--cursor`, …) is passed (the init command currently hardcodes `["claude-code"]`; extend it to read the new flags).

Helpers available in `render.ts`:

- `kitRoot(start)` — walk up from `dist/` to find `research-kit/`.
- `deepMergeJson(base, add)` — deep merge (concatenates arrays); use for settings files.
- `render(tpl, vars)` — `{{placeholder}}` substitution for neutral templates (`{{CLI}}`, `{{CMD_REF}}`, etc., per spec §6.3).

## Step 4 — golden-snapshot test

Each configurator gets a test that runs it against a temp repo and asserts the generated files (mirroring `packages/adapters/test/claude-code.test.ts`). The pattern:

```ts
import { describe, it, expect } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureCodex } from "../src/configurators/codex.js";

describe("configureCodex", () => {
  it("wires the per-turn hook and copies agents", () => {
    const repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-"));
    configureCodex(repo);
    const cfg = fs.readFileSync(path.join(repo, ".codex/config.toml"), "utf8");
    expect(cfg).toContain("rc context");                       // injection wired
    expect(fs.existsSync(path.join(repo, ".codex/agents"))).toBe(true);
    // re-run is idempotent
    configureCodex(repo);
    expect(fs.readFileSync(path.join(repo, ".codex/config.toml"), "utf8")).toBe(cfg);
  });
});
```

Assert: the injection wiring is present and points at `rc context`; agents are rendered into the right directory/format; and a second `configure<Platform>()` call leaves the files unchanged (idempotency). Compare against a checked-in golden where exact output matters. See [testing.md](testing.md) for running and adding tests.

## Checklist

- [ ] `ToolEntry` added to `AI_TOOLS` (fields per spec §6.1).
- [ ] Injection class chosen; hook (class-1) or breadcrumb rule (class-2) implemented.
- [ ] `configure<Platform>()` written, idempotent, exported from `index.ts`.
- [ ] `rc init` flag wired to call it.
- [ ] Golden-snapshot test added and green.
- [ ] No changes required in `core` — if you needed them, reconsider.
