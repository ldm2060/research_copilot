// MCP stdio server exposing three scholar tools (per spec §7):
//   - scholar_search   { query, limit?, backends? } -> aggregated Papers via the facade
//   - scholar_metadata { id }                       -> single arXiv metadata lookup
//   - bibtex           { query }                     -> a BibTeX string from DBLP
//
// The server delegates to the facade (failure-isolated, source-tagged) and the
// arxiv/dblp backends. Every tool wraps its body in try/catch and returns an
// isError result on failure rather than throwing across the transport.

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { searchScholar } from "./facade.js";
import { arxivMetadata } from "./backends/arxiv.js";
import { dblpBibtex, dblpSearch } from "./backends/dblp.js";

export function createServer(): McpServer {
  const server = new McpServer({
    name: "mcp-scholar",
    version: "0.0.0",
  });

  server.registerTool(
    "scholar_search",
    {
      title: "Search scholarly literature",
      description:
        "Search literature across multiple backends (default: arxiv + dblp; " +
        "scholar and arxivsub are opt-in best-effort). Per-backend failures are " +
        "isolated and every result is tagged with its source.",
      inputSchema: {
        query: z.string().describe("Free-text search query"),
        limit: z
          .number()
          .int()
          .positive()
          .optional()
          .describe("Max results per backend (default 10)"),
        backends: z
          .array(z.enum(["arxiv", "dblp", "scholar", "arxivsub"]))
          .optional()
          .describe('Backends to query (default ["arxiv","dblp"])'),
      },
    },
    async ({ query, limit, backends }) => {
      try {
        const papers = await searchScholar(query, { limit, backends });
        return {
          content: [{ type: "text", text: JSON.stringify(papers, null, 2) }],
          structuredContent: { papers },
        };
      } catch (err) {
        return errorResult("scholar_search", err);
      }
    },
  );

  server.registerTool(
    "scholar_metadata",
    {
      title: "Look up arXiv paper metadata",
      description:
        "Fetch metadata (title, authors, year, abstract, url) for a single arXiv " +
        "id (e.g. \"1706.03762\").",
      inputSchema: {
        id: z.string().describe("arXiv id, e.g. 1706.03762 or 2005.14165v4"),
      },
    },
    async ({ id }) => {
      try {
        const paper = await arxivMetadata(id);
        if (!paper) {
          return {
            content: [{ type: "text", text: `No arXiv metadata found for id "${id}"` }],
            structuredContent: { paper: null },
          };
        }
        return {
          content: [{ type: "text", text: JSON.stringify(paper, null, 2) }],
          structuredContent: { paper },
        };
      } catch (err) {
        return errorResult("scholar_metadata", err);
      }
    },
  );

  server.registerTool(
    "bibtex",
    {
      title: "Get a BibTeX entry",
      description:
        "Return a BibTeX entry for a query. Resolves the top DBLP hit and fetches " +
        "its .bib export. Returns an empty string when nothing is found.",
      inputSchema: {
        query: z.string().describe("Search query or DBLP record key"),
      },
    },
    async ({ query }) => {
      try {
        // Resolve the best DBLP hit, then fetch its bibtex. If the query already
        // looks like a DBLP key/url, dblpBibtex handles it directly.
        let key = query;
        if (!looksLikeDblpKeyOrUrl(query)) {
          const hits = await dblpSearch(query, 1);
          if (hits.length > 0 && hits[0].id) {
            key = hits[0].id;
          }
        }
        const bib = await dblpBibtex(key);
        return {
          content: [{ type: "text", text: bib }],
          structuredContent: { bibtex: bib },
        };
      } catch (err) {
        return errorResult("bibtex", err);
      }
    },
  );

  return server;
}

function looksLikeDblpKeyOrUrl(s: string): boolean {
  // DBLP record keys look like "conf/naacl/DevlinCLT19" or "journals/x/Solo21".
  return /^https?:\/\//.test(s) || /^[a-z]+\/[^\s]+\/[^\s]+$/i.test(s);
}

function errorResult(tool: string, err: unknown) {
  const message = err instanceof Error ? err.message : String(err);
  return {
    isError: true,
    content: [{ type: "text" as const, text: `${tool} failed: ${message}` }],
  };
}
