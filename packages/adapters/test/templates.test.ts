import { describe, it, expect } from "vitest";
import * as fs from "node:fs"; import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const KIT = path.resolve(__dirname, "../../../research-kit");
const agentFiles = [
  "rc-plan.md",
  "rc-literature.md",
  "rc-ideation.md",
  "rc-experiment.md",
  "rc-writer.md",
  "rc-polisher.md",
  "rc-reviewer.md",
  "rc-rebuttal.md",
  "rc-verify.md",
  "rc-update-spec.md",
];

describe("research-kit templates", () => {
  it("has workflow.md with all 5 state blocks", () => {
    const md = fs.readFileSync(path.join(KIT, "workflow.md"), "utf8");
    for (const s of ["no_task","planning","in_progress","verify","completed"])
      expect(md).toContain(`[workflow-state:${s}]`);
  });

  it("frames the workflow as Trellis conductor semantics", () => {
    const md = fs.readFileSync(path.join(KIT, "workflow.md"), "utf8");
    expect(md).toContain("MAIN SESSION = Trellis conductor");
    expect(md).toContain("Every research-domain action must belong to a .research/tasks/<id> task node");
    expect(md).toContain("If the user asks for research-domain work and there is no active task, create a task node first");
    expect(md).toContain("Do not consume the frontier yourself");
  });

  it("has 10 agent templates", () => {
    const agents = fs.readdirSync(path.join(KIT, "agents")).filter(f => f.endsWith(".md"));
    expect(agents.length).toBe(10);
  });

  it("all rc agents declare Trellis node ownership and recursion limits", () => {
    for (const file of agentFiles) {
      const md = fs.readFileSync(path.join(KIT, "agents", file), "utf8");
      expect(md).toContain("## Trellis Node Ownership");
      expect(md).toContain("You are a leaf executor for exactly one `.research/tasks/<id>` task node.");
      expect(md).toContain("Do NOT spawn other `rc-*` agents.");
      expect(md).toContain("Record gaps with `rc task add-gap <id> --desc \"<gap>\" --suggest <kind>`.");
    }
  });

  it("no agent template contains stale add-gap syntax missing <id>", () => {
    for (const file of agentFiles) {
      const md = fs.readFileSync(path.join(KIT, "agents", file), "utf8");
      expect(md).not.toContain("rc task add-gap --desc");
    }
  });
});
