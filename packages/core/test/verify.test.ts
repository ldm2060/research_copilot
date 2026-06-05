import { describe, it, expect } from "vitest";
import { numberTraceability, citationCompliance } from "../src/verify.js";

describe("verify checks (§16.2)", () => {
  it("number-traceability passes when every draft number appears in artifacts text", () => {
    const draft = "We reach 92.5 accuracy with 3 seeds.";
    const artifacts = "final_acc=92.5\nseeds=3\n";
    expect(numberTraceability(draft, artifacts)).toEqual({ ok: true, missing: [] });
  });
  it("number-traceability fails and reports a fabricated number", () => {
    const draft = "We reach 99.9 accuracy.";
    const artifacts = "final_acc=92.5\n";
    expect(numberTraceability(draft, artifacts)).toEqual({ ok: false, missing: ["99.9"] });
  });
  it("citation-compliance fails on a cite key absent from bibtex", () => {
    const tex = "Strong results \\cite{smith2020} and \\cite{ghost2099}.";
    const bib = "@article{smith2020, title={x}}";
    expect(citationCompliance(tex, bib)).toEqual({ ok: false, missing: ["ghost2099"] });
  });
  it("citation-compliance checks keys even with optional \\cite arguments", () => {
    const tex = "See \\cite[p.5]{smith2020} and \\citep[see][]{ghost2099}.";
    const bib = "@article{smith2020, title={x}}";
    expect(citationCompliance(tex, bib)).toEqual({ ok: false, missing: ["ghost2099"] });
  });
});
