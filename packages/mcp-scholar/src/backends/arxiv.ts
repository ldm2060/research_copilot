// arXiv backend — queries the arXiv Atom API and maps entries to Paper.
//
// API: GET http://export.arxiv.org/api/query?search_query=all:<q>&max_results=<n>
// Response: Atom 1.0 XML. Each <entry> carries:
//   <id>http://arxiv.org/abs/<arxiv-id>vN</id>
//   <title>...</title>
//   <summary>...</summary>            (the abstract)
//   <published>YYYY-MM-DDT...Z</published>
//   <author><name>...</name></author> (one or many)
//
// This backend is FULLY implemented (not best-effort): parse failures throw so
// the facade can isolate them, but it does not silently swallow errors itself.

import { XMLParser } from "fast-xml-parser";
import type { Paper } from "../types.js";

const ENDPOINT = "http://export.arxiv.org/api/query";

// fast-xml-parser config: keep single/array entries normalizable by us.
const parser = new XMLParser({
  ignoreAttributes: true,
  trimValues: true,
});

/** Coerce a fast-xml-parser field that may be a single value or an array. */
function toArray<T>(value: T | T[] | undefined): T[] {
  if (value === undefined || value === null) return [];
  return Array.isArray(value) ? value : [value];
}

/** Extract the bare arXiv id (e.g. "1706.03762") from the entry id URL. */
function arxivIdFromUrl(idUrl: string): string {
  // idUrl looks like "http://arxiv.org/abs/1706.03762v5"
  const match = idUrl.match(/abs\/(.+)$/);
  return match ? match[1] : idUrl;
}

interface AtomAuthor {
  name?: string;
}

interface AtomEntry {
  id?: string;
  title?: string;
  summary?: string;
  published?: string;
  author?: AtomAuthor | AtomAuthor[];
  link?: unknown;
}

export async function arxivSearch(
  query: string,
  limit: number,
  fetchImpl: typeof fetch = fetch,
): Promise<Paper[]> {
  const url = `${ENDPOINT}?search_query=all:${encodeURIComponent(query)}&max_results=${limit}`;
  const res = await fetchImpl(url);
  const xml = await res.text();
  const doc = parser.parse(xml) as { feed?: { entry?: AtomEntry | AtomEntry[] } };

  const entries = toArray(doc.feed?.entry);
  return entries.map((entry): Paper => {
    const idUrl = typeof entry.id === "string" ? entry.id : "";
    const authors = toArray(entry.author)
      .map((a) => (typeof a?.name === "string" ? a.name : ""))
      .filter((n) => n.length > 0);

    const published = typeof entry.published === "string" ? entry.published : undefined;
    const year = published ? Number(published.slice(0, 4)) : undefined;

    const title = typeof entry.title === "string" ? entry.title.trim() : "";
    const abstract =
      typeof entry.summary === "string" ? entry.summary.trim() : undefined;

    return {
      id: arxivIdFromUrl(idUrl),
      title,
      authors,
      year: Number.isFinite(year) ? year : undefined,
      abstract,
      url: idUrl || undefined,
      source: "arxiv",
    };
  });
}

/**
 * Fetch metadata for a single arXiv id. Used by the `scholar_metadata` tool.
 * Reuses the search endpoint with an id_list query and returns the first match
 * (or undefined when nothing comes back).
 */
export async function arxivMetadata(
  id: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Paper | undefined> {
  const url = `${ENDPOINT}?id_list=${encodeURIComponent(id)}&max_results=1`;
  const res = await fetchImpl(url);
  const xml = await res.text();
  const doc = parser.parse(xml) as { feed?: { entry?: AtomEntry | AtomEntry[] } };
  const entries = toArray(doc.feed?.entry);
  if (entries.length === 0) return undefined;

  const entry = entries[0];
  const idUrl = typeof entry.id === "string" ? entry.id : "";
  const authors = toArray(entry.author)
    .map((a) => (typeof a?.name === "string" ? a.name : ""))
    .filter((n) => n.length > 0);
  const published = typeof entry.published === "string" ? entry.published : undefined;
  const year = published ? Number(published.slice(0, 4)) : undefined;

  return {
    id: arxivIdFromUrl(idUrl),
    title: typeof entry.title === "string" ? entry.title.trim() : "",
    authors,
    year: Number.isFinite(year) ? year : undefined,
    abstract: typeof entry.summary === "string" ? entry.summary.trim() : undefined,
    url: idUrl || undefined,
    source: "arxiv",
  };
}
