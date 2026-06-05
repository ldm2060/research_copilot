import { describe, it, expect } from "vitest";
import { arxivSearch } from "../src/backends/arxiv.js";

// Canned arXiv Atom feed with two <entry> elements. The real API returns an
// Atom 1.0 document; we only model the fields the backend maps to Paper.
const ATOM_XML = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query: search_query=all:transformers</title>
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <updated>2023-08-02T00:41:18Z</updated>
    <published>2017-06-12T17:57:34Z</published>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex
recurrent or convolutional neural networks.</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <link href="http://arxiv.org/abs/1706.03762v5" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2005.14165v4</id>
    <updated>2020-07-22T00:00:00Z</updated>
    <published>2020-05-28T17:29:23Z</published>
    <title>Language Models are Few-Shot Learners</title>
    <summary>We train GPT-3, an autoregressive language model with 175 billion
parameters.</summary>
    <author><name>Tom B. Brown</name></author>
    <link href="http://arxiv.org/abs/2005.14165v4" rel="alternate" type="text/html"/>
  </entry>
</feed>`;

function makeMockFetch(body: string): typeof fetch {
  return (async (_input: RequestInfo | URL, _init?: RequestInit) => {
    return new Response(body, {
      status: 200,
      headers: { "content-type": "application/atom+xml" },
    });
  }) as typeof fetch;
}

describe("arxivSearch", () => {
  it("parses Atom XML into two source-tagged Papers", async () => {
    const papers = await arxivSearch("transformers", 2, makeMockFetch(ATOM_XML));
    expect(papers).toHaveLength(2);

    for (const p of papers) {
      expect(p.source).toBe("arxiv");
      expect(typeof p.title).toBe("string");
      expect(Array.isArray(p.authors)).toBe(true);
    }

    const [first, second] = papers;
    expect(first.title).toBe("Attention Is All You Need");
    expect(first.id).toContain("1706.03762");
    expect(first.authors).toEqual(["Ashish Vaswani", "Noam Shazeer"]);
    expect(first.abstract).toContain("sequence transduction");
    expect(first.year).toBe(2017);

    expect(second.title).toBe("Language Models are Few-Shot Learners");
    // Single-author entry must still produce an array, not a bare string.
    expect(second.authors).toEqual(["Tom B. Brown"]);
  });

  it("targets the arXiv query endpoint with the query and limit", async () => {
    let calledUrl = "";
    const spyFetch = (async (input: RequestInfo | URL) => {
      calledUrl = String(input);
      return new Response(ATOM_XML, { status: 200 });
    }) as typeof fetch;

    await arxivSearch("graph neural networks", 5, spyFetch);
    expect(calledUrl).toContain("export.arxiv.org/api/query");
    expect(calledUrl).toContain("max_results=5");
    expect(calledUrl).toContain("graph");
  });
});
