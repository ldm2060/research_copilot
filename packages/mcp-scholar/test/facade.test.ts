import { describe, it, expect } from "vitest";
import { searchScholar } from "../src/facade.js";
import type { Paper } from "../src/types.js";

// One canned arXiv entry — enough to prove the arxiv backend produced results.
const ATOM_XML = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <published>2022-01-01T00:00:00Z</published>
    <title>Isolated Failure Test Paper</title>
    <summary>An abstract.</summary>
    <author><name>A. Author</name></author>
  </entry>
</feed>`;

// A fetch impl that succeeds for the arXiv endpoint but THROWS for DBLP.
// This simulates one backend failing hard while another succeeds.
function arxivOkDblpThrows(): typeof fetch {
  return (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("export.arxiv.org")) {
      return new Response(ATOM_XML, { status: 200 });
    }
    if (url.includes("dblp.org")) {
      throw new Error("DBLP exploded");
    }
    // scholar / arxivsub endpoints: also blow up to prove they degrade to [].
    throw new Error("blocked");
  }) as typeof fetch;
}

describe("searchScholar facade", () => {
  it("isolates a thrown backend and still returns the other backend's results", async () => {
    const papers = await searchScholar("x", {
      backends: ["arxiv", "dblp"],
      fetchImpl: arxivOkDblpThrows(),
    });

    // DBLP threw; arxiv succeeded. The aggregate must contain the arxiv paper
    // and must NOT have propagated the DBLP error.
    expect(papers.length).toBeGreaterThanOrEqual(1);
    expect(papers.some((p: Paper) => p.source === "arxiv")).toBe(true);
    expect(papers.some((p: Paper) => p.title === "Isolated Failure Test Paper")).toBe(true);

    // Every result is source-tagged.
    for (const p of papers) {
      expect(typeof p.source).toBe("string");
      expect(p.source.length).toBeGreaterThan(0);
    }
  });

  it("defaults to arxiv + dblp when no backends are specified", async () => {
    let dblpHit = false;
    const fetchImpl = (async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("dblp.org")) dblpHit = true;
      return new Response(ATOM_XML, { status: 200 });
    }) as typeof fetch;

    await searchScholar("x", { fetchImpl });
    // dblp is part of the default set, so it should have been queried.
    expect(dblpHit).toBe(true);
  });

  it("scholar/arxivsub backends degrade to [] (blocked / no key) without breaking the aggregate", async () => {
    // arxiv succeeds; scholar is blocked; arxivsub has no key (env empty).
    const fetchImpl = (async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("export.arxiv.org")) {
        return new Response(ATOM_XML, { status: 200 });
      }
      // scholar endpoint -> simulate a block / captcha by throwing.
      throw new Error("HTTP 429 blocked");
    }) as typeof fetch;

    const papers = await searchScholar("x", {
      backends: ["arxiv", "scholar", "arxivsub"],
      fetchImpl,
    });

    // The blocked scholar backend and key-less arxivsub backend contribute
    // nothing but do not break the aggregate; arxiv results survive.
    expect(papers.some((p: Paper) => p.source === "arxiv")).toBe(true);
    expect(papers.every((p: Paper) => typeof p.source === "string")).toBe(true);
  });

  it("returns [] (not a throw) when every backend fails", async () => {
    const allFail = (async () => {
      throw new Error("everything is down");
    }) as typeof fetch;

    const papers = await searchScholar("x", {
      backends: ["arxiv", "dblp", "scholar", "arxivsub"],
      fetchImpl: allFail,
    });
    expect(papers).toEqual([]);
  });
});
