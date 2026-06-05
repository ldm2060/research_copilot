import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseSkillpacks } from "../src/parse-skillpacks.js";
import type { SkillpacksYaml } from "../src/skillpacks.js";

describe("parseSkillpacks", () => {
  it("parses valid YAML", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const yamlPath = join(tmp, "skillpacks.yaml");

    writeFileSync(yamlPath, `
packs:
  - name: research-kit
    description: Core research agents and specs
    source: https://github.com/research-copilot/research-kit.git
    version: v1.0.0
    enabled: true
  - name: review-pack
    description: Paper review agents
    source: https://github.com/research-copilot/review-pack.git
`);

    const result: SkillpacksYaml = parseSkillpacks(yamlPath);

    expect(result.packs.length).toBe(2);
    expect(result.packs[0].name).toBe("research-kit");
    expect(result.packs[0].source).toBe("https://github.com/research-copilot/research-kit.git");
    expect(result.packs[0].version).toBe("v1.0.0");
    expect(result.packs[0].enabled).toBe(true);
    expect(result.packs[1].name).toBe("review-pack");

    rmSync(tmp, { recursive: true, force: true });
  });

  it("throws on missing packs array", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const yamlPath = join(tmp, "skillpacks.yaml");

    writeFileSync(yamlPath, `foo: bar`);

    expect(() => parseSkillpacks(yamlPath)).toThrow(/must have 'packs' array/);

    rmSync(tmp, { recursive: true, force: true });
  });

  it("throws on pack missing name", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const yamlPath = join(tmp, "skillpacks.yaml");

    writeFileSync(yamlPath, `
packs:
  - source: https://example.com/repo.git
`);

    expect(() => parseSkillpacks(yamlPath)).toThrow(/must have a 'name'/);

    rmSync(tmp, { recursive: true, force: true });
  });

  it("throws on pack missing source", () => {
    const tmp = mkdtempSync(join(tmpdir(), "rc-test-"));
    const yamlPath = join(tmp, "skillpacks.yaml");

    writeFileSync(yamlPath, `
packs:
  - name: test-pack
    description: Test
`);

    expect(() => parseSkillpacks(yamlPath)).toThrow(/must have a 'source' URL/);

    rmSync(tmp, { recursive: true, force: true });
  });
});
