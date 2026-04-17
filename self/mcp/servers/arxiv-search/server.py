"""arXiv paper search & PDF download MCP server.

Provides two tools:
  - search_arxiv: search arXiv papers by keywords / author / arXiv ID
  - get_arxiv_pdf_url: get the direct PDF download URL for an arXiv paper

Uses the public arXiv API (Atom XML) — no API key required.
Rate limit: arXiv asks clients to keep one request per 3 seconds;
this server sends requests serially and does not batch.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

# Force binary unbuffered I/O on Windows pipes
if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


SERVER_NAME = "arxiv-search"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"
USER_AGENT = "research-copilot-arxiv-search/0.1"
MAX_RESULTS = 20

# Rate limiting & retry
MIN_REQUEST_INTERVAL = 3.0  # arXiv asks 1 req / 3s
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5  # seconds, doubles each retry
_last_request_time = 0.0

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_ABS_URL = "https://arxiv.org/abs"
ARXIV_PDF_URL = "https://arxiv.org/pdf"

ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"
OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"

TOOLS = [
    {
        "name": "search_arxiv",
        "title": "Search arXiv Papers",
        "description": (
            "Search arXiv for academic papers. Returns title, authors, abstract, "
            "arXiv ID, published date, categories, and PDF download URL for each match. "
            "Use this as the PRIMARY tool for any academic paper lookup."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query. Supports arXiv query syntax: "
                        'ti:"word" for title, au:"name" for author, abs:"text" for abstract, '
                        "cat:cs.CV for category. Plain text searches all fields. "
                        "You can also pass an arXiv ID like 1706.03762."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_RESULTS,
                    "default": 5,
                    "description": "Maximum number of papers to return.",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                    "default": "relevance",
                    "description": "Sort criterion for results.",
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["ascending", "descending"],
                    "default": "descending",
                    "description": "Sort direction.",
                },
                "start": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Offset for pagination (0-based index).",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_arxiv_pdf_url",
        "title": "Get arXiv PDF URL",
        "description": (
            "Given an arXiv ID (e.g. 1706.03762 or 2301.01234v2), "
            "return the direct PDF download URL and the abstract page URL."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "arxiv_id": {
                    "type": "string",
                    "description": "arXiv paper identifier, e.g. 1706.03762 or 2301.01234v2.",
                },
            },
            "required": ["arxiv_id"],
            "additionalProperties": False,
        },
    },
]


# ---------------------------------------------------------------------------
# MCP protocol helpers (identical to dblp-bib server)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _wait_rate_limit() -> None:
    """Enforce minimum interval between consecutive HTTP requests."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def http_get_text(url: str) -> str:
    """HTTP GET with rate limiting and retry on 429 / 5xx."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        _wait_rate_limit()
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code == 429 or exc.code >= 500:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                sys.stderr.write(
                    f"[{SERVER_NAME}] HTTP {exc.code} on attempt {attempt+1}/{MAX_RETRIES+1}, "
                    f"retrying in {wait}s…\n"
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
                    f"[{SERVER_NAME}] network error on attempt {attempt+1}/{MAX_RETRIES+1}: {exc}, "
                    f"retrying in {wait}s…\n"
                )
                sys.stderr.flush()
                time.sleep(wait)
                continue
            raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# arXiv helpers
# ---------------------------------------------------------------------------

def _build_search_query(query: str) -> str:
    """If the query looks like an arXiv ID, search by id_list instead."""
    arxiv_id_re = re.compile(
        r"^\d{4}\.\d{4,5}(v\d+)?$|^astro-ph|^cond-mat|^gr-qc|^hep-|^math-?|^nlin|^nucl-|^physics|^quant-ph|^cs\.|^econ\.|^eess\.|^math\s|^physics\.|^q-bio|^q-fin|^stat\."
    )
    stripped = query.strip()
    if arxiv_id_re.match(stripped):
        # Pure arXiv ID — will be used as id_list
        return stripped
    return stripped


def _is_arxiv_id(query: str) -> bool:
    """Check if query is a bare arXiv ID (e.g. 1706.03762)."""
    return bool(re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", query.strip()))


def _normalize_arxiv_id(raw_id: str) -> str:
    """Strip any URL prefix, keep only the ID portion."""
    raw_id = raw_id.strip()
    # Handle full URLs: https://arxiv.org/abs/1706.03762v1
    m = re.search(r"arxiv\.org/(?:abs|pdf|html)/(.+?)(?:\.pdf)?$", raw_id)
    if m:
        raw_id = m.group(1)
    # Remove version suffix for cleaner URL (keep it if user explicitly wants it)
    return raw_id


def _extract_pdf_url(entry: ET.Element, arxiv_id: str) -> str:
    """Get PDF URL from entry links or construct from ID."""
    for link in entry.findall(f"{{{ATOM_NS}}}link"):
        if link.get("title") == "pdf":
            href = link.get("href", "")
            if href:
                return href
    # Fallback: construct URL
    clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
    return f"{ARXIV_PDF_URL}/{clean_id}.pdf"


def _parse_entry(entry: ET.Element) -> dict[str, Any] | None:
    """Parse a single Atom <entry> into a structured dict."""
    # Title
    title_el = entry.find(f"{{{ATOM_NS}}}title")
    title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""

    # ID -> arxiv_id
    id_el = entry.find(f"{{{ATOM_NS}}}id")
    id_text = (id_el.text or "").strip() if id_el is not None else ""
    # Extract arXiv ID from URL like http://arxiv.org/abs/1706.03762v1
    arxiv_id_match = re.search(r"arxiv\.org/abs/(.+)$", id_text)
    arxiv_id = arxiv_id_match.group(1) if arxiv_id_match else id_text

    # Authors
    authors: list[str] = []
    for author_el in entry.findall(f"{{{ATOM_NS}}}author"):
        name_el = author_el.find(f"{{{ATOM_NS}}}name")
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    # Abstract / summary
    summary_el = entry.find(f"{{{ATOM_NS}}}summary")
    abstract = (summary_el.text or "").strip().replace("\n", " ") if summary_el is not None else ""

    # Published / updated
    published_el = entry.find(f"{{{ATOM_NS}}}published")
    published = published_el.text.strip()[:10] if published_el is not None and published_el.text else ""

    updated_el = entry.find(f"{{{ATOM_NS}}}updated")
    updated = updated_el.text.strip()[:10] if updated_el is not None and updated_el.text else ""

    # Categories
    categories: list[str] = []
    for cat_el in entry.findall(f"{{{ATOM_NS}}}category"):
        term = cat_el.get("term")
        if term:
            categories.append(term)
    primary_cat_el = entry.find(f"{{{ARXIV_NS}}}primary_category")
    primary_category = primary_cat_el.get("term", "") if primary_cat_el is not None else ""

    # Comment
    comment_el = entry.find(f"{{{ARXIV_NS}}}comment")
    comment = (comment_el.text or "").strip() if comment_el is not None else ""

    # DOI
    doi_el = entry.find(f"{{{ARXIV_NS}}}doi")
    doi = (doi_el.text or "").strip() if doi_el is not None else ""

    # PDF URL
    pdf_url = _extract_pdf_url(entry, arxiv_id)

    # Abstract page URL
    clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
    abs_url = f"{ARXIV_ABS_URL}/{clean_id}"

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published": published,
        "updated": updated,
        "categories": categories,
        "primary_category": primary_category,
        "comment": comment,
        "doi": doi,
        "pdf_url": pdf_url,
        "abs_url": abs_url,
    }


def _format_search_results(query: str, total: int, entries: list[dict[str, Any]]) -> str:
    """Format search results into human-readable text."""
    if not entries:
        return f"No arXiv papers found for query: {query}"

    lines = [f"Found {total} result(s) on arXiv (showing {len(entries)}):", ""]
    for idx, paper in enumerate(entries, start=1):
        lines.append(f"[{idx}] {paper['title']}")
        lines.append(f"  arXiv ID : {paper['arxiv_id']}")
        if paper["authors"]:
            author_str = ", ".join(paper["authors"])
            if len(author_str) > 120:
                author_str = author_str[:117] + "..."
            lines.append(f"  Authors  : {author_str}")
        if paper["published"]:
            lines.append(f"  Published: {paper['published']}")
        if paper["primary_category"]:
            lines.append(f"  Category : {paper['primary_category']}")
        if paper["doi"]:
            lines.append(f"  DOI      : {paper['doi']}")
        lines.append(f"  PDF      : {paper['pdf_url']}")
        lines.append(f"  Abstract : {paper['abs_url']}")
        if paper["abstract"]:
            # Truncate long abstracts in text output
            abstract_preview = paper["abstract"][:500]
            if len(paper["abstract"]) > 500:
                abstract_preview += "..."
            lines.append(f"  Summary  : {abstract_preview}")
        if paper["comment"]:
            lines.append(f"  Comment  : {paper['comment']}")
        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Sort parameter mapping
# ---------------------------------------------------------------------------

SORT_MAP = {
    "relevance": "relevance",
    "lastupdateddate": "lastUpdatedDate",
    "submitteddate": "submittedDate",
}

ORDER_MAP = {
    "ascending": "ascending",
    "descending": "descending",
}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_search_arxiv(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        return tool_error("The query argument is required.")

    max_results = max(1, min(int(arguments.get("max_results", 5)), MAX_RESULTS))
    start = max(0, int(arguments.get("start", 0)))
    sort_by = str(arguments.get("sort_by", "relevance")).strip()
    sort_order = str(arguments.get("sort_order", "descending")).strip()

    params: dict[str, str] = {
        "max_results": str(max_results),
        "start": str(start),
        "sortBy": SORT_MAP.get(sort_by.lower(), "relevance"),
        "sortOrder": ORDER_MAP.get(sort_order.lower(), "descending"),
    }

    # If query looks like arXiv ID, use id_list for exact match
    if _is_arxiv_id(query):
        params["id_list"] = query
        params["search_query"] = ""
    else:
        params["search_query"] = query

    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"

    try:
        xml_text = http_get_text(url)
        root = ET.fromstring(xml_text)
    except urllib.error.URLError as exc:
        return tool_error(f"arXiv API request failed: {exc}")
    except ET.ParseError as exc:
        return tool_error(f"Failed to parse arXiv response XML: {exc}")

    # Total results
    total_el = root.find(f"{{{OPENSEARCH_NS}}}totalResults")
    total = int(total_el.text) if total_el is not None and total_el.text else 0

    # Parse entries
    entries: list[dict[str, Any]] = []
    for entry_el in root.findall(f"{{{ATOM_NS}}}entry"):
        parsed = _parse_entry(entry_el)
        if parsed:
            entries.append(parsed)

    text_output = _format_search_results(query, total, entries)
    return {
        "content": [{"type": "text", "text": text_output}],
        "structuredContent": {
            "query": query,
            "total_results": total,
            "returned": len(entries),
            "start": start,
            "papers": entries,
        },
        "isError": False,
    }


def tool_get_arxiv_pdf_url(arguments: dict[str, Any]) -> dict[str, Any]:
    raw_id = str(arguments.get("arxiv_id", "")).strip()
    if not raw_id:
        return tool_error("The arxiv_id argument is required.")

    arxiv_id = _normalize_arxiv_id(raw_id)
    clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id

    pdf_url = f"{ARXIV_PDF_URL}/{clean_id}.pdf"
    abs_url = f"{ARXIV_ABS_URL}/{clean_id}"

    text = f"arXiv Paper: {clean_id}\nAbstract page: {abs_url}\nPDF download: {pdf_url}"
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": {
            "arxiv_id": clean_id,
            "full_id": arxiv_id,
            "abs_url": abs_url,
            "pdf_url": pdf_url,
        },
        "isError": False,
    }


def tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


# ---------------------------------------------------------------------------
# Request router
# ---------------------------------------------------------------------------

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
        if tool_name == "search_arxiv":
            send_result(request_id, tool_search_arxiv(arguments))
            return
        if tool_name == "get_arxiv_pdf_url":
            send_result(request_id, tool_get_arxiv_pdf_url(arguments))
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
