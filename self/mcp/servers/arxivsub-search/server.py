"""arXivSub MCP server.

Provides conference-aware academic paper search through the arXIVSub API.
This keeps arxivsub-specific network logic inside MCP rather than skill-local
scripts, while the arxivsub-skill remains a thin orchestration layer.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    import msvcrt

    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


SERVER_NAME = "arxivsub-search"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"
API_URL = "https://qtevnmgyobilaanrzidq.supabase.co/functions/v1/agent-skills-gateway"
VALID_LOCATIONS = ["arxiv", "CVPR", "ICCV", "ICLR", "ICML", "NeurIPS", "AAAI", "MICCAI"]
DEFAULT_LIMIT = 10
MAX_LIMIT = 50

TOOLS = [
    {
        "name": "search_papers",
        "title": "Search arXIVSub Papers",
        "description": (
            "Search arXiv and supported AI/CV conference papers through the arXIVSub API. "
            "Returns full structured paper details, including paper summaries, key methods, "
            "results, affiliations, PDF URLs, and remaining daily quota."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string.",
                },
                "locations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": VALID_LOCATIONS,
                    },
                    "description": "Sources to search. Valid values: arxiv, CVPR, ICCV, ICLR, ICML, NeurIPS, AAAI, MICCAI.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_LIMIT,
                    "default": DEFAULT_LIMIT,
                    "description": "Maximum number of papers to return.",
                },
                "arxiv_days": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional recency window for arXiv results, in days.",
                },
                "conference_years": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional conference years filter.",
                },
                "language": {
                    "type": "string",
                    "default": "en",
                    "description": "Language hint forwarded to the arXIVSub API, for example en or zh.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }
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


def make_text_result(text: str, structured: dict[str, Any] | None = None, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }
    if structured is not None:
        result["structuredContent"] = structured
    return result


def load_api_key() -> str | None:
    key = os.environ.get("ARXIVSUB_SKILL_KEY", "").strip()
    if key:
        return key

    env_file = Path.cwd() / ".env"
    if env_file.is_file():
        for raw_line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if line.startswith("ARXIVSUB_SKILL_KEY="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
    return None


def _parse_summary(summary_content: str) -> dict[str, str]:
    segments = summary_content.split("<SEG>")
    content = segments[1:] if len(segments) == 11 else segments

    if len(content) < 10:
        return {
            "what_about": summary_content[:300],
            "innovations": "",
            "techniques": "",
            "datasets": "",
            "results": "",
            "limitations": "",
        }

    return {
        "what_about": content[0].strip(),
        "innovations": content[1].strip(),
        "techniques": content[2].strip(),
        "datasets": content[3].strip(),
        "results": content[4].strip(),
        "limitations": content[5].strip(),
    }


def parse_response(raw: str) -> tuple[list[dict[str, Any]], Any]:
    data = json.loads(raw)

    all_papers = []
    for source in ("arxiv", "conferences"):
        for paper in data.get(source, []):
            paper["_source"] = source
            all_papers.append(paper)

    papers: list[dict[str, Any]] = []
    for paper in all_papers:
        parsed = _parse_summary(paper.get("summary_content", ""))

        authors = paper.get("authors", [])
        first = next((author for author in authors if author.get("is_first_author")), authors[0] if authors else {})
        last = next((author for author in authors if author.get("is_last_author")), authors[-1] if authors else {})

        papers.append(
            {
                "id": paper.get("id"),
                "title": paper.get("title"),
                "source": paper.get("_source"),
                "conference": paper.get("conference_name", "arXiv"),
                "year": paper.get("publish_year"),
                "arxiv_id": paper.get("arxiv_id"),
                "pdf_url": paper.get("pdf_url"),
                "first_author": first.get("name", ""),
                "first_aff": first.get("affiliation", ""),
                "last_author": last.get("name", ""),
                "last_aff": last.get("affiliation", ""),
                "keywords": [keyword["name"] for keyword in paper.get("keywords", []) if "name" in keyword],
                **parsed,
            }
        )

    return papers, data.get("quota_remaining")


def classify_http_error(status_code: int, body: str) -> tuple[str, str]:
    body_lower = body.lower()
    if status_code in {401, 403} or "unauthorized" in body_lower or "invalid" in body_lower and "key" in body_lower:
        return (
            "auth_failure",
            "arXIVSub authentication failed. Check ARXIVSUB_SKILL_KEY in your environment or .env file.",
        )
    if status_code == 429 or "quota" in body_lower or "limit" in body_lower and "daily" in body_lower:
        return (
            "quota_exhausted",
            "The arXIVSub daily quota appears to be exhausted. Wait for reset or switch to another paper-search path.",
        )
    if status_code >= 500:
        return (
            "server_error",
            "The arXIVSub service returned a temporary server error. Retry later.",
        )
    return (
        "http_error",
        f"arXIVSub request failed with HTTP {status_code}: {body.strip() or 'no response body'}",
    )


def tool_search_papers(arguments: dict[str, Any]) -> dict[str, Any]:
    api_key = load_api_key()
    if not api_key:
        return make_text_result(
            "ARXIVSUB_SKILL_KEY is not set. Configure it either as an environment variable or in a .env file at the workspace root.",
            {
                "error_type": "missing_api_key",
                "env_var": "ARXIVSUB_SKILL_KEY",
            },
            is_error=True,
        )

    query = str(arguments.get("query", "")).strip()
    if not query:
        return make_text_result(
            "Query must be a non-empty string.",
            {"error_type": "invalid_input", "field": "query"},
            is_error=True,
        )

    locations = arguments.get("locations") or ["arxiv"]
    if not isinstance(locations, list) or not all(isinstance(location, str) for location in locations):
        return make_text_result(
            "locations must be an array of source names.",
            {"error_type": "invalid_input", "field": "locations"},
            is_error=True,
        )

    invalid_locations = [location for location in locations if location not in VALID_LOCATIONS]
    if invalid_locations:
        return make_text_result(
            "Unsupported locations: " + ", ".join(invalid_locations),
            {
                "error_type": "invalid_input",
                "field": "locations",
                "valid_locations": VALID_LOCATIONS,
            },
            is_error=True,
        )

    limit = int(arguments.get("limit", DEFAULT_LIMIT))
    language = str(arguments.get("language", "en") or "en")
    arxiv_days = arguments.get("arxiv_days")
    conference_years = arguments.get("conference_years")

    body: dict[str, Any] = {
        "query": query,
        "language": language,
        "locations": locations,
        "limit": limit,
    }
    if arxiv_days is not None:
        body["arxiv_days"] = int(arxiv_days)
    if conference_years is not None:
        body["conference_years"] = conference_years

    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-agent-skill-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        error_type, message = classify_http_error(exc.code, error_body)
        return make_text_result(
            message,
            {
                "error_type": error_type,
                "status_code": exc.code,
                "details": error_body.strip(),
            },
            is_error=True,
        )
    except urllib.error.URLError as exc:
        return make_text_result(
            f"arXIVSub request failed: {exc.reason}",
            {
                "error_type": "network_error",
                "details": str(exc.reason),
            },
            is_error=True,
        )

    try:
        papers, quota_remaining = parse_response(raw)
    except json.JSONDecodeError as exc:
        return make_text_result(
            "arXIVSub returned an unexpected non-JSON response.",
            {
                "error_type": "json_parse_error",
                "details": str(exc),
            },
            is_error=True,
        )

    filters = {
        "locations": locations,
        "limit": limit,
        "language": language,
        "arxiv_days": arxiv_days,
        "conference_years": conference_years,
    }
    structured = {
        "query": query,
        "filters": filters,
        "quota_remaining": quota_remaining,
        "total_papers": len(papers),
        "papers": papers,
    }

    lines = [
        f"Found {len(papers)} papers for query: {query}",
        f"Locations: {', '.join(locations)}",
    ]
    if arxiv_days is not None:
        lines.append(f"arXiv days: {arxiv_days}")
    if conference_years:
        lines.append("Conference years: " + ", ".join(str(year) for year in conference_years))
    if quota_remaining is not None:
        lines.append(f"Quota remaining: {quota_remaining}")
    if papers:
        lines.extend(["", "Top titles:"])
        for index, paper in enumerate(papers[:5], start=1):
            venue = paper.get("conference") or paper.get("source") or "unknown"
            year = paper.get("year") or "?"
            lines.append(f"{index}. {paper.get('title', '(untitled)')} [{venue} {year}]")
    else:
        lines.append("No papers matched the current filters.")

    return make_text_result("\n".join(lines), structured, is_error=False)


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
        if tool_name != "search_papers":
            send_error(request_id, -32602, f"Unknown tool: {tool_name}")
            return
        try:
            send_result(request_id, tool_search_papers(arguments))
        except Exception as exc:
            send_result(
                request_id,
                make_text_result(
                    f"Tool {tool_name} failed: {exc}",
                    {"error_type": "internal_error"},
                    is_error=True,
                ),
            )
        return

    if request_id is not None:
        send_error(request_id, -32601, f"Method not found: {method}")


def main() -> int:
    while True:
        message = read_message()
        if message is None:
            return 0
        handle_request(message)


if __name__ == "__main__":
    raise SystemExit(main())