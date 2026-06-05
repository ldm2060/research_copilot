// DBLP backend — queries the DBLP publication search API and maps hits to Paper.
//
// Search API: GET https://dblp.org/search/publ/api?q=<q>&format=json&h=<limit>
// Response shape (the parts we use):
//   { result: { hits: { hit: [ { info: {
//       title, authors: { author: [{ text }] | { text } }, year, url, key
//   } } ] } } }
//
// BibTeX: DBLP exposes a .bib export at <rec-url>.bib. dblpBibtex fetches it and
// returns the raw bibtex string; on ANY failure it returns "" (never throws).
//
// This backend is FULLY implemented (search parsing is tested). Search parse
// errors propagate so the facade can isolate them per-backend.

import type { Paper } from "../types.js";

const SEARCH_ENDPOINT = "https://dblp.org/search/publ/api";

function toArray<T>(value: T | T[] | undefined): T[] {
  if (value === undefined || value === null) return [];
  return Array.isArray(value) ? value : [value];
}

interface DblpAuthor {
  text?: string;
}

interface DblpInfo {
  title?: string;
  authors?: { author?: DblpAuthor | DblpAuthor[] };
  year?: string | number;
  url?: string;
  key?: string;
  doi?: string;
}

interface DblpResponse {
  result?: { hits?: { hit?: Array<{ info?: DblpInfo }> } };
}

export async function dblpSearch(
  query: string,
  limit: number,
  fetchImpl: typeof fetch = fetch,
): Promise<Paper[]> {
  const url = `${SEARCH_ENDPOINT}?q=${encodeURIComponent(query)}&format=json&h=${limit}`;
  const res = await fetchImpl(url);
  const json = (await res.json()) as DblpResponse;

  const hits = toArray(json.result?.hits?.hit);
  return hits.map((hit): Paper => {
    const info = hit.info ?? {};
    const authors = toArray(info.authors?.author)
      .map((a) => (typeof a?.text === "string" ? a.text : ""))
      .filter((n) => n.length > 0);

    const yearNum = info.year !== undefined ? Number(info.year) : undefined;

    return {
      id: typeof info.key === "string" ? info.key : (info.url ?? ""),
      title: typeof info.title === "string" ? info.title : "",
      authors,
      year: yearNum !== undefined && Number.isFinite(yearNum) ? yearNum : undefined,
      url: typeof info.url === "string" ? info.url : undefined,
      source: "dblp",
    };
  });
}

/**
 * Fetch a BibTeX entry from DBLP. `keyOrUrl` may be a DBLP record key
 * (e.g. "conf/naacl/DevlinCLT19") or a full record URL. On any error returns "".
 */
export async function dblpBibtex(
  keyOrUrl: string,
  fetchImpl: typeof fetch = fetch,
): Promise<string> {
  try {
    const url = bibtexUrl(keyOrUrl);
    const res = await fetchImpl(url);
    if (!res.ok) return "";
    const text = await res.text();
    return text;
  } catch (err) {
    process.stderr.write(
      `mcp-scholar: dblpBibtex failed for "${keyOrUrl}": ${errMsg(err)}\n`,
    );
    return "";
  }
}

function bibtexUrl(keyOrUrl: string): string {
  // Full record URL -> append .bib (DBLP serves <rec-url>.bib).
  if (/^https?:\/\//.test(keyOrUrl)) {
    return keyOrUrl.endsWith(".bib") ? keyOrUrl : `${keyOrUrl}.bib`;
  }
  // Bare record key -> canonical rec URL.
  return `https://dblp.org/rec/${keyOrUrl}.bib`;
}

function errMsg(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
