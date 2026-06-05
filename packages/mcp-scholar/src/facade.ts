// Scholar facade — a thin aggregator over the literature backends.
//
// CORRECTNESS CONTRACT (spec §7, §15.5):
//   1. FAILURE ISOLATION: each backend runs inside its own try/catch. A backend
//      that throws (network error, parse error, block) contributes [] and logs
//      to stderr; the error is NEVER propagated out of the facade. One broken
//      backend cannot kill the others.
//   2. SOURCE TAGGING: every returned Paper carries the `source` set by its
//      backend ("arxiv" | "dblp" | "scholar" | "arxivsub").
//   3. DEFAULTS: arxiv + dblp run by default; scholar + arxivsub are opt-in
//      (best-effort, degrade to []).
//
// The facade export is named `searchScholar` to avoid clashing with the Google
// Scholar backend's `scholarSearch`; that backend is imported under an alias.

import type { Paper } from "./types.js";
import { arxivSearch } from "./backends/arxiv.js";
import { dblpSearch } from "./backends/dblp.js";
import { scholarSearch as googleScholarSearch } from "./backends/scholar.js";
import { arxivsubSearch } from "./backends/arxivsub.js";

export interface ScholarOptions {
  limit?: number;
  backends?: string[];
  fetchImpl?: typeof fetch;
}

const DEFAULT_BACKENDS = ["arxiv", "dblp"];
const DEFAULT_LIMIT = 10;

export async function searchScholar(
  query: string,
  opts: ScholarOptions = {},
): Promise<Paper[]> {
  const limit = opts.limit ?? DEFAULT_LIMIT;
  const backends = opts.backends ?? DEFAULT_BACKENDS;
  const fetchImpl = opts.fetchImpl ?? fetch;

  // Run selected backends concurrently, each isolated. A rejected/throwing
  // backend yields [] (logged) and does not reject the aggregate.
  const tasks = backends.map((name) => runBackend(name, query, limit, fetchImpl));
  const results = await Promise.all(tasks);
  return results.flat();
}

async function runBackend(
  name: string,
  query: string,
  limit: number,
  fetchImpl: typeof fetch,
): Promise<Paper[]> {
  try {
    switch (name) {
      case "arxiv":
        return await arxivSearch(query, limit, fetchImpl);
      case "dblp":
        return await dblpSearch(query, limit, fetchImpl);
      case "scholar":
        // Best-effort backend; already degrades to [] internally, but wrap it
        // anyway for defense in depth.
        return await googleScholarSearch(query, limit, fetchImpl);
      case "arxivsub":
        return await arxivsubSearch(query, limit, fetchImpl);
      default:
        process.stderr.write(`mcp-scholar: unknown backend "${name}" ignored\n`);
        return [];
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    process.stderr.write(
      `mcp-scholar: backend "${name}" failed (isolated): ${message}\n`,
    );
    return [];
  }
}
