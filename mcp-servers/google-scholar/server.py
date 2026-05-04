from __future__ import annotations

"""Google Scholar search MCP server.

This server performs direct Google Scholar page requests and enriches each
result with Scholar citation formats. Abstract values are Scholar snippets,
not full publisher abstracts.
"""

import html
import http.cookiejar
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

if sys.platform == "win32":
    import msvcrt

    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


SERVER_NAME = "google-scholar"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-03-26"
MAX_LIMIT = 3
DEFAULT_LIMIT = 1
MAX_METADATA_LIMIT = 10
DEFAULT_METADATA_LIMIT = 5
DEFAULT_TIMEOUT = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)

MIN_REQUEST_INTERVAL = 2.0
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5
CHAINED_REQUEST_JITTER_RANGE = (0.35, 1.0)
_last_request_time = 0.0

SCHOLAR_BASE_URL = "https://scholar.google.com"
SCHOLAR_SEARCH_URL = f"{SCHOLAR_BASE_URL}/scholar"
SCHOLAR_CITE_URL_TEMPLATE = (
    f"{SCHOLAR_BASE_URL}/scholar?q=info:{{id}}:scholar.google.com/&output=cite&scirp={{p}}&hl={{hl}}"
)
BLOCK_PAGE_MARKERS = (
    "unusual traffic from your computer network",
    "detected unusual traffic",
    "please show you're not a robot",
    "not a robot",
    "gs_captcha",
    "/sorry/",
)

COOKIE_JAR = http.cookiejar.CookieJar()
HTTP_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))

TOOLS = [
    {
        "name": "search_google_scholar_metadata",
        "title": "Search Google Scholar Metadata",
        "description": (
            "Search Google Scholar and return paper metadata only, without citation-style "
            "or export-format enrichment. Abstract values are Scholar result snippets."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text Google Scholar query.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_METADATA_LIMIT,
                    "default": DEFAULT_METADATA_LIMIT,
                    "description": "Maximum number of Scholar papers to return without citation enrichment.",
                },
                "start": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Scholar pagination offset.",
                },
                "hl": {
                    "type": "string",
                    "default": "en",
                    "description": "Scholar language code, for example en.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_google_scholar",
        "title": "Search Google Scholar",
        "description": (
            "Search Google Scholar and return per-paper metadata plus Scholar citation styles "
            "and export formats. Abstract values are Scholar result snippets. Use this when "
            "you need citation enrichment, not just metadata."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text Google Scholar query.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_LIMIT,
                    "default": DEFAULT_LIMIT,
                    "description": "Maximum number of Scholar papers to enrich.",
                },
                "start": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Scholar pagination offset.",
                },
                "hl": {
                    "type": "string",
                    "default": "en",
                    "description": "Scholar language code, for example en.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }
]


class ScholarBlockedError(RuntimeError):
    pass


class ScholarSearchResultsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, Any]] = []
        self.current_result: dict[str, Any] | None = None
        self.current_result_div_depth = 0
        self.in_title = False
        self.title_anchor_active = False
        self.title_buffer: list[str] = []
        self.capture_authors = False
        self.authors_div_depth = 0
        self.authors_buffer: list[str] = []
        self.capture_abstract = False
        self.abstract_div_depth = 0
        self.abstract_buffer: list[str] = []
        self.footer_anchor_active = False
        self.footer_anchor_href = ""
        self.footer_anchor_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: (value or "") for key, value in attrs}
        class_names = set(attrs_dict.get("class", "").split())

        if tag == "div":
            if self.current_result is None and "gs_r" in class_names and "gs_or" in class_names:
                scholar_id = attrs_dict.get("data-cid") or attrs_dict.get("data-did")
                if scholar_id:
                    self.current_result = {
                        "scholar_id": scholar_id,
                        "rank": int(attrs_dict.get("data-rp") or len(self.results)),
                        "title": "",
                        "url": "",
                        "authors_line": "",
                        "authors": [],
                        "venue": "",
                        "year": "",
                        "abstract": "",
                        "cited_by_count": 0,
                        "cited_by_url": "",
                        "related_articles_url": "",
                        "versions_url": "",
                        "resource_url": "",
                        "resource_label": "",
                    }
                    self.current_result_div_depth = 1
                    return
            elif self.current_result is not None:
                self.current_result_div_depth += 1
                if self.capture_authors:
                    self.authors_div_depth += 1
                if self.capture_abstract:
                    self.abstract_div_depth += 1

            if self.current_result is not None and "gs_a" in class_names and not self.capture_authors:
                self.capture_authors = True
                self.authors_div_depth = 1
                self.authors_buffer = []
                return

            if self.current_result is not None and "gs_rs" in class_names and not self.capture_abstract:
                self.capture_abstract = True
                self.abstract_div_depth = 1
                self.abstract_buffer = []
                return

        if self.current_result is None:
            return

        if tag == "h3" and "gs_rt" in class_names:
            self.in_title = True
            return

        if tag == "a":
            href = attrs_dict.get("href", "")
            if self.in_title and not self.title_anchor_active and href and not href.startswith("javascript:"):
                self.title_anchor_active = True
                self.current_result["url"] = resolve_url(href)
                self.title_buffer = []
                return

            if not self.in_title and not self.capture_authors and not self.capture_abstract and href:
                self.footer_anchor_active = True
                self.footer_anchor_href = resolve_url(href)
                self.footer_anchor_buffer = []
                return

        if tag == "br" and self.capture_abstract:
            self.abstract_buffer.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self.current_result is None:
            return

        if tag == "a":
            if self.title_anchor_active:
                self.current_result["title"] = normalize_space("".join(self.title_buffer))
                self.title_anchor_active = False
                self.title_buffer = []
                return

            if self.footer_anchor_active:
                self._consume_footer_anchor()
                self.footer_anchor_active = False
                self.footer_anchor_href = ""
                self.footer_anchor_buffer = []
                return

        if tag == "h3" and self.in_title:
            self.in_title = False
            return

        if tag == "div":
            if self.capture_authors:
                self.authors_div_depth -= 1
                if self.authors_div_depth == 0:
                    self.current_result["authors_line"] = normalize_space("".join(self.authors_buffer))
                    self.capture_authors = False
                    self.authors_buffer = []

            if self.capture_abstract:
                self.abstract_div_depth -= 1
                if self.abstract_div_depth == 0:
                    self.current_result["abstract"] = normalize_space("".join(self.abstract_buffer))
                    self.capture_abstract = False
                    self.abstract_buffer = []

            self.current_result_div_depth -= 1
            if self.current_result_div_depth == 0:
                self._finalize_current_result()

    def handle_data(self, data: str) -> None:
        if self.title_anchor_active:
            self.title_buffer.append(data)
        if self.capture_authors:
            self.authors_buffer.append(data)
        if self.capture_abstract:
            self.abstract_buffer.append(data)
        if self.footer_anchor_active:
            self.footer_anchor_buffer.append(data)

    def _consume_footer_anchor(self) -> None:
        if self.current_result is None:
            return

        text = normalize_space("".join(self.footer_anchor_buffer))
        if not text:
            return

        if text.startswith("Cited by "):
            match = re.search(r"(\d+)", text)
            self.current_result["cited_by_count"] = int(match.group(1)) if match else 0
            self.current_result["cited_by_url"] = self.footer_anchor_href
            return

        if text == "Related articles":
            self.current_result["related_articles_url"] = self.footer_anchor_href
            return

        if text.startswith("All ") and " versions" in text:
            self.current_result["versions_url"] = self.footer_anchor_href
            return

        if text.startswith("[") and "]" in text and not self.current_result.get("resource_url"):
            self.current_result["resource_url"] = self.footer_anchor_href
            self.current_result["resource_label"] = text

    def _finalize_current_result(self) -> None:
        if self.current_result is None:
            return

        authors, venue, year = parse_authors_metadata(self.current_result.get("authors_line", ""))
        self.current_result["authors"] = authors
        self.current_result["venue"] = venue
        self.current_result["year"] = year
        self.results.append(self.current_result)
        self.current_result = None
        self.current_result_div_depth = 0
        self.in_title = False
        self.title_anchor_active = False
        self.capture_authors = False
        self.capture_abstract = False
        self.footer_anchor_active = False


def send_message(payload: dict[str, Any]) -> None:
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(line.encode("utf-8"))
    sys.stdout.buffer.flush()


def send_result(request_id: Any, result: dict[str, Any]) -> None:
    send_message({"jsonrpc": "2.0", "id": request_id, "result": result})


def send_error(request_id: Any, code: int, message: str) -> None:
    send_message({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def read_message() -> dict[str, Any] | None:
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    return json.loads(line.decode("utf-8"))


def normalize_space(value: str) -> str:
    value = html.unescape(value).replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def resolve_url(url: str) -> str:
    return urllib.parse.urljoin(SCHOLAR_BASE_URL, html.unescape(url))


def _wait_rate_limit() -> None:
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _sleep_chained_jitter() -> None:
    time.sleep(random.uniform(*CHAINED_REQUEST_JITTER_RANGE))


def _headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _decode_response(response: Any, payload: bytes) -> str:
    charset = response.headers.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _is_block_page(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in BLOCK_PAGE_MARKERS)


def http_get_text(url: str, *, referer: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        _wait_rate_limit()
        request = urllib.request.Request(url, headers=_headers(referer))
        try:
            with HTTP_OPENER.open(request, timeout=timeout) as response:
                text = _decode_response(response, response.read())
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (403, 429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                sys.stderr.write(
                    f"[{SERVER_NAME}] HTTP {exc.code} on attempt {attempt + 1}/{MAX_RETRIES + 1}, retrying in {wait}s...\n"
                )
                sys.stderr.flush()
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                sys.stderr.write(
                    f"[{SERVER_NAME}] network error on attempt {attempt + 1}/{MAX_RETRIES + 1}: {exc}, retrying in {wait}s...\n"
                )
                sys.stderr.flush()
                time.sleep(wait)
                continue
            raise

        if _is_block_page(text):
            last_exc = ScholarBlockedError("Google Scholar returned a block or CAPTCHA page.")
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                sys.stderr.write(
                    f"[{SERVER_NAME}] block page on attempt {attempt + 1}/{MAX_RETRIES + 1}, retrying in {wait}s...\n"
                )
                sys.stderr.flush()
                time.sleep(wait)
                continue
            raise last_exc

        return text

    raise last_exc or RuntimeError("Scholar request failed.")


def strip_tags(html_text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", html_text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return normalize_space(text)


def parse_authors_metadata(line: str) -> tuple[list[str], str, str]:
    normalized = normalize_space(line)
    if not normalized:
        return [], "", ""

    parts = [part.strip() for part in re.split(r"\s+-\s+", normalized) if part.strip()]
    author_part = parts[0] if parts else normalized
    author_tokens = [token.strip(" ,") for token in author_part.split(",")]
    authors: list[str] = []
    for token in author_tokens:
        cleaned = token.replace("...", "").replace("…", "").strip()
        if cleaned:
            authors.append(cleaned)

    year_match = re.findall(r"(?:19|20)\d{2}", normalized)
    year = year_match[-1] if year_match else ""

    venue = ""
    if len(parts) >= 2:
        venue = re.sub(r",\s*(?:19|20)\d{2}\s*$", "", parts[1]).strip(" ,;")

    return authors, venue, year


def build_search_url(query: str, limit: int, start: int, hl: str) -> str:
    params = {
        "q": query,
        "hl": hl,
        "as_sdt": "0,5",
        "start": str(start),
        "num": str(limit),
    }
    return f"{SCHOLAR_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def build_cite_url(scholar_id: str, rank: int, hl: str) -> str:
    return SCHOLAR_CITE_URL_TEMPLATE.format(id=scholar_id, p=rank, hl=hl)


def parse_search_results(html_text: str) -> list[dict[str, Any]]:
    parser = ScholarSearchResultsParser()
    parser.feed(html_text)
    parser.close()
    return parser.results


STYLE_ROW_RE = re.compile(
    r"<th[^>]*class=\"gs_cith\"[^>]*>(?P<label>.*?)</th>\s*<td><div[^>]*class=\"gs_citr\"[^>]*>(?P<value>.*?)</div>",
    re.IGNORECASE | re.DOTALL,
)
EXPORT_LINK_RE = re.compile(
    r"<a[^>]*class=\"gs_citi\"[^>]*href=\"(?P<href>[^\"]+)\"[^>]*>(?P<label>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
AUTHOR_FIELD_RE = re.compile(r"author\s*=\s*\{(?P<authors>.*?)\}\s*,?", re.IGNORECASE | re.DOTALL)


def parse_citation_popup(html_text: str) -> tuple[dict[str, str], dict[str, str]]:
    text_styles: dict[str, str] = {}
    export_links: dict[str, str] = {}

    for match in STYLE_ROW_RE.finditer(html_text):
        label = strip_tags(match.group("label"))
        value = strip_tags(match.group("value"))
        if label and value:
            text_styles[label] = value

    for match in EXPORT_LINK_RE.finditer(html_text):
        label = strip_tags(match.group("label"))
        href = resolve_url(match.group("href"))
        if label and href:
            export_links[label] = href

    return text_styles, export_links


def fetch_export_content(label: str, url: str, referer: str) -> dict[str, str]:
    payload = http_get_text(url, referer=referer)
    return {"url": url, "content": payload.strip()}


def extract_authors_from_bibtex(bibtex: str) -> list[str]:
    match = AUTHOR_FIELD_RE.search(bibtex)
    if not match:
        return []

    authors_block = normalize_space(match.group("authors"))
    if not authors_block:
        return []

    return [part.strip() for part in authors_block.split(" and ") if part.strip()]


def enrich_result_with_citations(result: dict[str, Any], hl: str, search_referer: str) -> dict[str, Any]:
    scholar_id = str(result.get("scholar_id", "")).strip()
    rank = int(result.get("rank", 0))
    cite_url = build_cite_url(scholar_id, rank, hl)
    warnings: list[str] = []

    _sleep_chained_jitter()
    popup_html = http_get_text(cite_url, referer=search_referer)
    text_styles, export_links = parse_citation_popup(popup_html)

    exports: dict[str, dict[str, str]] = {}
    for label, url in export_links.items():
        try:
            _sleep_chained_jitter()
            exports[label] = fetch_export_content(label, url, cite_url)
        except Exception as exc:
            warnings.append(f"Failed to fetch {label}: {exc}")

    bibtex_entry = exports.get("BibTeX", {}).get("content", "")
    full_authors = extract_authors_from_bibtex(bibtex_entry)
    if full_authors:
        result["authors"] = full_authors

    result["citation_formats"] = {
        "text_styles": text_styles,
        "exports": exports,
    }
    result["cite_url"] = cite_url
    result["warnings"] = warnings
    return result


def format_result_text(query: str, papers: list[dict[str, Any]], warnings: list[str]) -> str:
    return format_result_text_with_options(query, papers, warnings, include_citations=True)


def format_result_text_with_options(
    query: str,
    papers: list[dict[str, Any]],
    warnings: list[str],
    *,
    include_citations: bool,
) -> str:
    if not papers:
        return f"No Google Scholar results found for query: {query}"

    lines = [f"Found {len(papers)} Google Scholar result(s) for query: {query}", ""]
    for index, paper in enumerate(papers, start=1):
        lines.append(f"[{index}] {paper.get('title', '')}")
        if paper.get("url"):
            lines.append(f"url: {paper['url']}")
        if paper.get("authors"):
            lines.append(f"authors: {', '.join(paper['authors'])}")
        elif paper.get("authors_line"):
            lines.append(f"authors: {paper['authors_line']}")
        if paper.get("venue"):
            lines.append(f"venue: {paper['venue']}")
        if paper.get("year"):
            lines.append(f"year: {paper['year']}")
        if paper.get("abstract"):
            lines.append(f"abstract: {paper['abstract']}")
        if paper.get("cited_by_count"):
            lines.append(f"cited by: {paper['cited_by_count']}")

        if include_citations:
            citation_formats = paper.get("citation_formats", {})
            text_styles = citation_formats.get("text_styles", {})
            exports = citation_formats.get("exports", {})
            if text_styles:
                lines.append("text styles:")
                for label, text in text_styles.items():
                    lines.append(f"  {label}: {text}")
            if exports:
                lines.append("export formats:")
                for label, export in exports.items():
                    lines.append(f"  {label}:")
                    lines.append(export.get("content", ""))

        for warning in paper.get("warnings", []):
            lines.append(f"warning: {warning}")
        lines.append("")

    for warning in warnings:
        lines.append(f"warning: {warning}")

    return "\n".join(lines).strip()


def _search_google_scholar_metadata(
    query: str,
    *,
    limit: int,
    start: int,
    hl: str,
) -> tuple[list[dict[str, Any]], list[str], str]:
    search_url = build_search_url(query, limit, start, hl)
    html_text = http_get_text(search_url)
    papers = parse_search_results(html_text)[:limit]
    return papers, [], search_url


def search_google_scholar_metadata(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        return tool_error("The query argument is required.")

    limit = max(1, min(int(arguments.get("limit", DEFAULT_METADATA_LIMIT)), MAX_METADATA_LIMIT))
    start = max(0, int(arguments.get("start", 0)))
    hl = str(arguments.get("hl", "en")).strip() or "en"

    try:
        papers, warnings, _ = _search_google_scholar_metadata(query, limit=limit, start=start, hl=hl)
    except ScholarBlockedError as exc:
        return tool_error(f"Google Scholar blocked the request: {exc}")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return tool_error(f"Google Scholar lookup failed: {exc}")

    text_output = format_result_text_with_options(query, papers, warnings, include_citations=False)
    return {
        "content": [{"type": "text", "text": text_output}],
        "structuredContent": {
            "query": query,
            "count": len(papers),
            "start": start,
            "limit": limit,
            "hl": hl,
            "papers": papers,
            "warnings": warnings,
        },
        "isError": False,
    }


def search_google_scholar(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        return tool_error("The query argument is required.")

    limit = max(1, min(int(arguments.get("limit", DEFAULT_LIMIT)), MAX_LIMIT))
    start = max(0, int(arguments.get("start", 0)))
    hl = str(arguments.get("hl", "en")).strip() or "en"

    try:
        papers, _, search_url = _search_google_scholar_metadata(query, limit=limit, start=start, hl=hl)
    except ScholarBlockedError as exc:
        return tool_error(f"Google Scholar blocked the request: {exc}")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return tool_error(f"Google Scholar lookup failed: {exc}")

    warnings: list[str] = []
    enriched_papers: list[dict[str, Any]] = []
    for paper in papers:
        try:
            enriched_papers.append(enrich_result_with_citations(paper, hl, search_url))
        except ScholarBlockedError as exc:
            paper["citation_formats"] = {"text_styles": {}, "exports": {}}
            paper["warnings"] = [f"Citation fetch blocked: {exc}"]
            warnings.append(f"Scholar blocked citation enrichment for {paper.get('title', 'unknown title')}")
            enriched_papers.append(paper)
        except Exception as exc:
            paper["citation_formats"] = {"text_styles": {}, "exports": {}}
            paper["warnings"] = [f"Citation fetch failed: {exc}"]
            enriched_papers.append(paper)

    text_output = format_result_text(query, enriched_papers, warnings)
    return {
        "content": [{"type": "text", "text": text_output}],
        "structuredContent": {
            "query": query,
            "count": len(enriched_papers),
            "start": start,
            "limit": limit,
            "hl": hl,
            "papers": enriched_papers,
            "warnings": warnings,
        },
        "isError": False,
    }


def tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def handle_request(message: dict[str, Any]) -> None:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params", {}) or {}

    if method == "initialize":
        requested_protocol = params.get("protocolVersion") or PROTOCOL_VERSION
        send_result(
            request_id,
            {
                "protocolVersion": requested_protocol,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
        return

    if method == "notifications/initialized":
        return

    if method == "ping":
        send_result(request_id, {})
        return

    if method == "tools/list":
        send_result(request_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {}) or {}
        if tool_name == "search_google_scholar_metadata":
            send_result(request_id, search_google_scholar_metadata(arguments))
            return
        if tool_name == "search_google_scholar":
            send_result(request_id, search_google_scholar(arguments))
            return
        send_error(request_id, -32602, f"Unknown tool: {tool_name}")
        return

    if request_id is not None:
        send_error(request_id, -32601, f"Method not found: {method}")


def main() -> int:
    sys.stderr.write(f"[{SERVER_NAME}] started (pid={os.getpid()})\n")
    sys.stderr.flush()
    while True:
        message = read_message()
        if message is None:
            sys.stderr.write(f"[{SERVER_NAME}] stdin closed, exiting\n")
            sys.stderr.flush()
            return 0
        method = message.get("method", "?")
        sys.stderr.write(f"[{SERVER_NAME}] recv: {method}\n")
        sys.stderr.flush()
        try:
            handle_request(message)
        except Exception as exc:
            sys.stderr.write(f"[{SERVER_NAME}] error handling {method}: {exc}\n")
            sys.stderr.flush()
            if "id" in message:
                send_error(message["id"], -32603, f"Internal error: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())