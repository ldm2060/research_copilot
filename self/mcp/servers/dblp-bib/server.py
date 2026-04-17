from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# Force binary unbuffered I/O on Windows pipes
if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


SERVER_NAME = "dblp-bib"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"
USER_AGENT = "research-copilot-dblp-bib/0.1"
MAX_LIMIT = 10

# Rate limiting & retry
MIN_REQUEST_INTERVAL = 1.5  # DBLP asks clients to be polite
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5  # seconds, doubles each retry
_last_request_time = 0.0
DBLP_SEARCH_URL = "https://dblp.org/search/publ/api"
DBLP_BIB_URL = "https://dblp.org/rec/{key}.bib"
DBLP_REC_URL_RE = re.compile(r"https?://dblp\.org/rec/(?P<key>[^?#]+)")

TOOLS = [
    {
        "name": "search_dblp_bibtex",
        "title": "Search DBLP BibTeX",
        "description": "Search DBLP publications and return BibTeX entries for the top matches.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text DBLP publication query, typically title keywords, author names, or DOI.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_LIMIT,
                    "default": 5,
                    "description": "Maximum number of DBLP matches to return.",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Result offset for pagination.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_dblp_bibtex",
        "title": "Get DBLP BibTeX",
        "description": "Fetch a BibTeX entry directly from a DBLP record key or DBLP record URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key_or_url": {
                    "type": "string",
                    "description": "DBLP record key like conf/nips/VaswaniSPUJGKP17 or a full DBLP record URL.",
                }
            },
            "required": ["key_or_url"],
            "additionalProperties": False,
        },
    },
]


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


def _wait_rate_limit() -> None:
    """Enforce minimum interval between consecutive HTTP requests."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def http_get_json(url: str) -> dict[str, Any]:
    """HTTP GET JSON with rate limiting and retry on 429 / 5xx."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        _wait_rate_limit()
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
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


def http_get_text(url: str) -> str:
    """HTTP GET text with rate limiting and retry on 429 / 5xx."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        _wait_rate_limit()
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
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


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_author_names(info: dict[str, Any]) -> list[str]:
    author_block = info.get("authors", {}).get("author")
    names: list[str] = []
    for author in as_list(author_block):
        if isinstance(author, dict):
            text = author.get("text")
            if text:
                names.append(str(text))
        elif author:
            names.append(str(author))
    return names


def normalize_record_key(key_or_url: str) -> str:
    value = key_or_url.strip()
    match = DBLP_REC_URL_RE.match(value)
    if match:
        value = match.group("key")
    value = value.removesuffix(".html").removesuffix(".bib")
    return value.strip("/")


def fetch_bibtex_for_key(record_key: str) -> str:
    safe_key = urllib.parse.quote(record_key, safe="/")
    bib_url = DBLP_BIB_URL.format(key=safe_key)
    return http_get_text(bib_url).strip()


def format_search_text(query: str, entries: list[dict[str, Any]]) -> str:
    if not entries:
        return f"No DBLP matches found for query: {query}"

    lines = [f"Found {len(entries)} DBLP match(es) for query: {query}", ""]
    for index, entry in enumerate(entries, start=1):
        lines.append(f"[{index}] {entry['title']}")
        lines.append(f"key: {entry['key']}")
        if entry.get("authors"):
            lines.append(f"authors: {', '.join(entry['authors'])}")
        if entry.get("venue"):
            lines.append(f"venue: {entry['venue']}")
        if entry.get("year"):
            lines.append(f"year: {entry['year']}")
        if entry.get("doi"):
            lines.append(f"doi: {entry['doi']}")
        lines.append("")
        lines.append(entry["bibtex"])
        lines.append("")
    return "\n".join(lines).strip()


def search_dblp_bibtex(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        return tool_error("The query argument is required.")

    limit = max(1, min(int(arguments.get("limit", 5)), MAX_LIMIT))
    offset = max(0, int(arguments.get("offset", 0)))
    params = urllib.parse.urlencode({"q": query, "format": "json", "h": limit, "f": offset, "c": 0})

    try:
        payload = http_get_json(f"{DBLP_SEARCH_URL}?{params}")
        hits = payload.get("result", {}).get("hits", {}).get("hit")
        entries: list[dict[str, Any]] = []
        for hit in as_list(hits):
            info = hit.get("info", {}) if isinstance(hit, dict) else {}
            record_key = info.get("key")
            if not record_key:
                continue
            bibtex = fetch_bibtex_for_key(str(record_key))
            entries.append(
                {
                    "key": str(record_key),
                    "title": html.unescape(str(info.get("title", ""))).strip(),
                    "authors": extract_author_names(info),
                    "venue": str(info.get("venue", "")).strip(),
                    "year": str(info.get("year", "")).strip(),
                    "type": str(info.get("type", "")).strip(),
                    "doi": str(info.get("doi", "")).strip(),
                    "url": str(info.get("url", "")).strip(),
                    "bibtex": bibtex,
                }
            )
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return tool_error(f"DBLP lookup failed: {exc}")

    return {
        "content": [{"type": "text", "text": format_search_text(query, entries)}],
        "structuredContent": {"query": query, "count": len(entries), "entries": entries},
        "isError": False,
    }


def get_dblp_bibtex(arguments: dict[str, Any]) -> dict[str, Any]:
    key_or_url = str(arguments.get("key_or_url", "")).strip()
    if not key_or_url:
        return tool_error("The key_or_url argument is required.")

    record_key = normalize_record_key(key_or_url)
    if not record_key:
        return tool_error("Could not parse a DBLP record key from key_or_url.")

    try:
        bibtex = fetch_bibtex_for_key(record_key)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return tool_error(f"Failed to fetch BibTeX for {record_key}: {exc}")

    return {
        "content": [{"type": "text", "text": bibtex}],
        "structuredContent": {"key": record_key, "bibtex": bibtex},
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
        if tool_name == "search_dblp_bibtex":
            send_result(request_id, search_dblp_bibtex(arguments))
            return
        if tool_name == "get_dblp_bibtex":
            send_result(request_id, get_dblp_bibtex(arguments))
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