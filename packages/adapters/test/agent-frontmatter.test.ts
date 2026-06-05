import { describe, it, expect } from "vitest";
import { parseAgent } from "../src/agent-frontmatter.js";

describe("parseAgent", () => {
  it("parses name/description/kind/model + body (quoted or bare)", () => {
    const a = parseAgent("---\nname: rc-writer\ndescription: \"Drafts sections\"\nkind: writing\nmodel: sonnet\n---\nBody line one.\nBody line two.");
    expect(a.name).toBe("rc-writer");
    expect(a.description).toBe("Drafts sections");
    expect(a.kind).toBe("writing");
    expect(a.model).toBe("sonnet");
    expect(a.body).toBe("Body line one.\nBody line two.");
  });
  it("normalizes CRLF in the body to LF", () => {
    const a = parseAgent("---\r\nname: x\r\ndescription: y\r\n---\r\nL1\r\nL2\r\n");
    expect(a.body).toBe("L1\nL2");
  });
  it("throws when name is missing/empty (loud failure for malformed templates)", () => {
    expect(() => parseAgent("Just a body, no frontmatter")).toThrow(/name/i);
    expect(() => parseAgent("---\ndescription: y\n---\nbody")).toThrow(/name/i);
  });
});
