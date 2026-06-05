import { describe, it, expect } from "vitest";
import { KINDS, STATUSES, isKind } from "../src/types.js";

describe("types", () => {
  it("exposes the 7 research kinds", () => {
    expect(KINDS).toEqual([
      "literature","ideation","experiment","writing","polish","review","rebuttal"
    ]);
  });
  it("exposes the lifecycle statuses in order", () => {
    expect(STATUSES).toEqual(["planning","in_progress","verify","completed"]);
  });
  it("isKind narrows valid kinds", () => {
    expect(isKind("writing")).toBe(true);
    expect(isKind("nope")).toBe(false);
  });
});
