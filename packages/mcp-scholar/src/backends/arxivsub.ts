// arxivsub backend — BEST-EFFORT only, behind a 3rd-party gateway.
//
// arxivsub is a 3rd-party arXiv submission/search gateway that requires an API
// key supplied via the ARXIVSUB_SKILL_KEY environment variable. If the key is
// absent the backend returns [] immediately (it is opt-in and unconfigured by
// default). When a key IS present it does a single best-effort JSON fetch; on
// ANY error it returns [] and NEVER throws.
//
// Intentionally minimal and not unit-tested against the live gateway. The
// response shape below is a defensive guess; unknown shapes degrade to [].

import type { Paper } from "../types.js";

const ENDPOINT = "https://arxivsub.com/api/search";

interface ArxivsubItem {
  id?: string;
  arxiv_id?: string;
  title?: string;
  authors?: string[] | string;
  year?: number | string;
  abstract?: string;
  summary?: string;
  url?: string;
}

interface ArxivsubResponse {
  results?: ArxivsubItem[];
  items?: ArxivsubItem[];
  data?: ArxivsubItem[];
}

export async function arxivsubSearch(
  query: string,
  limit: number,
  fetchImpl: typeof fetch = fetch,
  env: NodeJS.ProcessEnv = process.env,
): Promise<Paper[]> {
  const key = env.ARXIVSUB_SKILL_KEY;
  if (!key) {
    // Unconfigured: silently opt out. Not an error.
    return [];
  }

  try {
    const url = `${ENDPOINT}?q=${encodeURIComponent(query)}&limit=${limit}`;
    const res = await fetchImpl(url, {
      headers: { authorization: `Bearer ${key}`, accept: "application/json" },
    });
    if (!res.ok) return [];

    const json = (await res.json()) as ArxivsubResponse;
    const items = json.results ?? json.items ?? json.data ?? [];
    if (!Array.isArray(items)) return [];

    return items.slice(0, limit).map((item): Paper => {
      const authors = Array.isArray(item.authors)
        ? item.authors
        : typeof item.authors === "string"
          ? [item.authors]
          : [];
      const yearNum = item.year !== undefined ? Number(item.year) : undefined;
      return {
        id: String(item.id ?? item.arxiv_id ?? item.url ?? item.title ?? ""),
        title: typeof item.title === "string" ? item.title : "",
        authors,
        year: yearNum !== undefined && Number.isFinite(yearNum) ? yearNum : undefined,
        abstract: item.abstract ?? item.summary,
        url: typeof item.url === "string" ? item.url : undefined,
        source: "arxivsub",
      };
    });
  } catch (err) {
    process.stderr.write(
      `mcp-scholar: arxivsub backend degraded to []: ${errMsg(err)}\n`,
    );
    return [];
  }
}

function errMsg(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
