// Google Scholar backend — BEST-EFFORT only.
//
// Google Scholar has no public API and aggressively blocks scrapers (captchas,
// 429s, HTML shape changes). This backend does a single minimal HTML fetch and a
// best-effort regex parse of result titles. On ANY error, block, captcha, or
// unparseable response it returns [] and NEVER throws — the facade relies on
// this so one blocked backend cannot break the aggregate.
//
// Intentionally minimal: this is not a robust scraper and is not unit-tested
// against live HTML. Treat results as opportunistic.

import type { Paper } from "../types.js";

const ENDPOINT = "https://scholar.google.com/scholar";

export async function scholarSearch(
  query: string,
  limit: number,
  fetchImpl: typeof fetch = fetch,
): Promise<Paper[]> {
  try {
    const url = `${ENDPOINT}?q=${encodeURIComponent(query)}&hl=en&num=${limit}`;
    const res = await fetchImpl(url, {
      headers: {
        // A desktop UA reduces (does not eliminate) bot blocking.
        "user-agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "accept-language": "en-US,en;q=0.9",
      },
    });

    if (!res.ok) return [];
    const html = await res.text();

    // A captcha/consent interstitial means we were blocked — degrade silently.
    if (/captcha|unusual traffic|not a robot/i.test(html)) return [];

    return parseScholarHtml(html, limit);
  } catch (err) {
    process.stderr.write(
      `mcp-scholar: scholar backend degraded to []: ${errMsg(err)}\n`,
    );
    return [];
  }
}

/**
 * Best-effort extraction of result titles from a Google Scholar results page.
 * Scholar wraps each result title in `<h3 class="gs_rt">...<a ...>TITLE</a>...`.
 * We pull the anchor text (or the raw h3 text when there is no link) and strip
 * tags. This is fragile by design; failure yields [].
 */
function parseScholarHtml(html: string, limit: number): Paper[] {
  const papers: Paper[] = [];
  const h3Re = /<h3[^>]*class="[^"]*gs_rt[^"]*"[^>]*>([\s\S]*?)<\/h3>/gi;
  let m: RegExpExecArray | null;
  while ((m = h3Re.exec(html)) !== null && papers.length < limit) {
    const inner = m[1];
    const anchor = inner.match(/<a[^>]*>([\s\S]*?)<\/a>/i);
    const rawTitle = anchor ? anchor[1] : inner;
    const title = stripTags(rawTitle).trim();
    if (!title) continue;
    const href = inner.match(/<a[^>]*href="([^"]+)"/i)?.[1];
    papers.push({
      id: href ?? title,
      title,
      authors: [],
      url: href,
      source: "scholar",
    });
  }
  return papers;
}

function stripTags(s: string): string {
  return s
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"');
}

function errMsg(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
