import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { parse as parseToml } from "smol-toml";
import { configureCodex } from "../src/configurators/codex.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("codex configurator", () => {
  it("renders the 10 agents as flat TOML with developer_instructions", () => {
    configureCodex(repo);
    const dir = path.join(repo, ".codex/agents");
    const tomls = fs.readdirSync(dir).filter(f => f.endsWith(".toml"));
    expect(tomls.length).toBe(10);
    const writer = parseToml(fs.readFileSync(path.join(dir, "rc-writer.toml"), "utf8")) as any;
    expect(writer.name).toBe("rc-writer");
    expect(typeof writer.description).toBe("string");
    expect(typeof writer.developer_instructions).toBe("string");
    expect(writer.developer_instructions.length).toBeGreaterThan(10);
  });
  it("writes a UserPromptSubmit hook calling rc context and enables hooks in config.toml", () => {
    configureCodex(repo);
    const hooksRaw = fs.readFileSync(path.join(repo, ".codex/hooks.json"), "utf8");
    expect(hooksRaw).toContain("rc context");
    expect(hooksRaw).toContain("UserPromptSubmit");
    const cfg = parseToml(fs.readFileSync(path.join(repo, ".codex/config.toml"), "utf8")) as any;
    expect(cfg.features.hooks).toBe(true);
  });
  it("is idempotent (re-run: still 10 agents, hooks.features.hooks still true, no dup hook)", () => {
    configureCodex(repo); configureCodex(repo);
    expect(fs.readdirSync(path.join(repo, ".codex/agents")).filter(f=>f.endsWith(".toml")).length).toBe(10);
    const cfg = parseToml(fs.readFileSync(path.join(repo, ".codex/config.toml"), "utf8")) as any;
    expect(cfg.features.hooks).toBe(true);
    const hooks = JSON.parse(fs.readFileSync(path.join(repo, ".codex/hooks.json"), "utf8"));
    const ups = hooks.UserPromptSubmit ?? hooks.hooks?.UserPromptSubmit ?? [];
    const cmds = (ups as any[]).flatMap(g => g.hooks ?? []).filter((h:any)=>String(h.command).includes("rc context"));
    expect(cmds.length).toBe(1);
  });
});
