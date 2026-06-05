import { describe, it, expect } from "vitest";
import { dblpSearch, dblpBibtex } from "../src/backends/dblp.js";

// Canned DBLP publ search response. DBLP returns year as a string and may
// return authors.author as either an array (multiple) or a single object.
const DBLP_JSON = JSON.stringify({
  result: {
    hits: {
      hit: [
        {
          info: {
            title: "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding.",
            authors: {
              author: [
                { text: "Jacob Devlin" },
                { text: "Ming-Wei Chang" },
                { text: "Kenton Lee" },
                { text: "Kristina Toutanova" },
              ],
            },
            year: "2019",
            url: "https://dblp.org/rec/conf/naacl/DevlinCLT19",
            key: "conf/naacl/DevlinCLT19",
          },
        },
        {
          info: {
            title: "A single-author paper.",
            // Single author: DBLP collapses to a bare object, not an array.
            authors: { author: { text: "Solo Researcher" } },
            year: "2021",
            url: "https://dblp.org/rec/journals/x/Solo21",
            key: "journals/x/Solo21",
          },
        },
      ],
    },
  },
});

function makeMockFetch(body: string): typeof fetch {
  return (async (_input: RequestInfo | URL) => {
    return new Response(body, { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
}

describe("dblpSearch", () => {
  it("parses DBLP JSON into source-tagged Papers", async () => {
    const papers = await dblpSearch("bert", 2, makeMockFetch(DBLP_JSON));
    expect(papers).toHaveLength(2);

    for (const p of papers) {
      expect(p.source).toBe("dblp");
    }

    const [first, second] = papers;
    expect(first.title).toContain("BERT");
    expect(first.year).toBe(2019);
    expect(first.url).toBe("https://dblp.org/rec/conf/naacl/DevlinCLT19");
    expect(first.authors).toEqual([
      "Jacob Devlin",
      "Ming-Wei Chang",
      "Kenton Lee",
      "Kristina Toutanova",
    ]);

    // Single author collapses to a bare object in DBLP; must normalize to array.
    expect(second.authors).toEqual(["Solo Researcher"]);
    expect(second.year).toBe(2021);
  });

  it("targets the DBLP publ API with query and limit", async () => {
    let calledUrl = "";
    const spyFetch = (async (input: RequestInfo | URL) => {
      calledUrl = String(input);
      return new Response(DBLP_JSON, { status: 200 });
    }) as typeof fetch;

    await dblpSearch("attention", 7, spyFetch);
    expect(calledUrl).toContain("dblp.org/search/publ/api");
    expect(calledUrl).toContain("format=json");
    expect(calledUrl).toContain("h=7");
  });
});

describe("dblpBibtex", () => {
  it("returns the fetched bibtex string", async () => {
    const BIB = "@inproceedings{DBLP:conf/naacl/DevlinCLT19,\n  title = {BERT}\n}";
    const fetchBib = (async () => new Response(BIB, { status: 200 })) as typeof fetch;
    const bib = await dblpBibtex("conf/naacl/DevlinCLT19", fetchBib);
    expect(bib).toContain("@inproceedings");
    expect(bib).toContain("BERT");
  });

  it("returns empty string on fetch failure (never throws)", async () => {
    const failFetch = (async () => {
      throw new Error("network down");
    }) as typeof fetch;
    const bib = await dblpBibtex("anything", failFetch);
    expect(bib).toBe("");
  });
});
