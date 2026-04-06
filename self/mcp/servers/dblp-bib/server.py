from __future__ import annotations

import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


SERVER_NAME = "dblp-bib"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"
USER_AGENT = "research-copilot-dblp-bib/0.1"
MAX_LIMIT = 10
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
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def send_result(request_id: Any, result: dict[str, Any]) -> None:
    send_message({"jsonrpc": "2.0", "id": request_id, "result": result})


def send_error(request_id: Any, code: int, message: str) -> None:
    send_message({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        header = line.decode("ascii").strip()
        if not header:
            continue
        name, value = header.split(":", 1)
        headers[name.lower()] = value.strip()

    content_length = headers.get("content-length")
    if content_length is None:
        return None
    raw_body = sys.stdin.buffer.read(int(content_length))
    if not raw_body:
        return None
    return json.loads(raw_body.decode("utf-8"))


def http_get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


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
    while True:
        message = read_message()
        if message is None:
            return 0
        try:
            handle_request(message)
        except Exception as exc:
            if "id" in message:
                send_error(message["id"], -32603, f"Internal error: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())