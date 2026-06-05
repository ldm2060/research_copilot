import { describe, it, expect } from "vitest";
import { extractWorkflowState } from "../src/workflow.js";

const MD = `# workflow
[workflow-state:planning]
Plan the task.
[/workflow-state]

[workflow-state:in_progress]
Dispatch the rc-{kind} executor.
[/workflow-state]
`;

describe("extractWorkflowState", () => {
  it("extracts the body of a named state block", () => {
    expect(extractWorkflowState(MD, "in_progress")).toBe("Dispatch the rc-{kind} executor.");
  });
  it("returns null for an absent state", () => {
    expect(extractWorkflowState(MD, "completed")).toBeNull();
  });
});
