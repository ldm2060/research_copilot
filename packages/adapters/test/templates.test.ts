import { describe, it, expect } from "vitest";
import * as fs from "node:fs"; import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const KIT = path.resolve(__dirname, "../../../research-kit");

describe("research-kit templates", () => {
  it("has workflow.md with all 5 state blocks", () => {
    const md = fs.readFileSync(path.join(KIT, "workflow.md"), "utf8");
    for (const s of ["no_task","planning","in_progress","verify","completed"])
      expect(md).toContain(`[workflow-state:${s}]`);
  });
  it("has 10 agent templates", () => {
    const agents = fs.readdirSync(path.join(KIT, "agents")).filter(f => f.endsWith(".md"));
    expect(agents.length).toBe(10);
  });
});
