import { describe, it, expect } from "vitest";
import { canTransition, assertTransition, nextStatuses } from "../src/lifecycle.js";

describe("lifecycle FSM", () => {
  it("allows the forward path", () => {
    expect(canTransition("planning", "in_progress")).toBe(true);
    expect(canTransition("in_progress", "verify")).toBe(true);
    expect(canTransition("verify", "completed")).toBe(true);
  });
  it("allows verify->in_progress rollback", () => {
    expect(canTransition("verify", "in_progress")).toBe(true);
  });
  it("rejects illegal jumps", () => {
    expect(canTransition("planning", "completed")).toBe(false);
    expect(canTransition("completed", "in_progress")).toBe(false);
  });
  it("assertTransition throws on illegal", () => {
    expect(() => assertTransition("planning", "completed")).toThrow(/illegal transition/i);
  });
  it("nextStatuses lists legal successors", () => {
    expect(nextStatuses("verify").sort()).toEqual(["completed", "in_progress"]);
  });
});
