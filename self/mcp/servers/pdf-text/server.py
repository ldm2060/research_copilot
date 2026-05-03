"""PDF text extraction MCP server.

Provides one tool:
  - extract_pdf_text: extract text from a local PDF file, page by page

Uses pdfplumber (preferred) or PyPDF2 as fallback.
Requires: pip install pdfplumber  (or pip install PyPDF2 as fallback)
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# Force binary unbuffered I/O on Windows pipes
if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


SERVER_NAME = "pdf-text"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-03-26"
MAX_PAGES_LIMIT = 200

TOOLS = [
    {
        "name": "extract_pdf_text",
        "title": "Extract PDF Text",
        "description": (
            "Extract text content from a local PDF file page by page. "
            "Returns structured text with page boundaries. "
            "Use this to read the full text of academic papers saved locally."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pdf_path": {
                    "type": "string",
                    "description": (
                        "Absolute or workspace-relative path to the PDF file. "
                        "Supports forward slashes on all platforms."
                    ),
                },
                "max_pages": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_PAGES_LIMIT,
                    "default": 0,
                    "description": (
                        "Maximum number of pages to extract. "
                        "0 means extract all pages."
                    ),
                },
                "start_page": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                    "description": "First page to extract (1-based index).",
                },
            },
            "required": ["pdf_path"],
            "additionalProperties": False,
        },
    },
]


# ---------------------------------------------------------------------------
# MCP protocol helpers
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
# PDF extraction helpers
# ---------------------------------------------------------------------------

def _resolve_path(path: str) -> str:
    """Resolve a possibly-relative path to absolute."""
    if os.path.isabs(path):
        return os.path.normpath(path)
    # Treat as relative to CWD
    return os.path.normpath(os.path.join(os.getcwd(), path))


def _extract_with_pdfplumber(
    pdf_path: str, start_page: int, max_pages: int
) -> tuple[list[dict[str, Any]], int]:
    """Extract text using pdfplumber. Returns (pages, total_pages)."""
    import pdfplumber

    pages_out: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        # Determine slice
        s = max(0, start_page - 1)
        e = total_pages if max_pages == 0 else min(s + max_pages, total_pages)

        for i in range(s, e):
            text = pdf.pages[i].extract_text() or ""
            pages_out.append({
                "page": i + 1,
                "text": text,
            })
    return pages_out, total_pages


def _extract_with_pypdf2(
    pdf_path: str, start_page: int, max_pages: int
) -> tuple[list[dict[str, Any]], int]:
    """Extract text using PyPDF2 as fallback. Returns (pages, total_pages)."""
    from PyPDF2 import PdfReader

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    s = max(0, start_page - 1)
    e = total_pages if max_pages == 0 else min(s + max_pages, total_pages)

    pages_out: list[dict[str, Any]] = []
    for i in range(s, e):
        text = reader.pages[i].extract_text() or ""
        pages_out.append({
            "page": i + 1,
            "text": text,
        })
    return pages_out, total_pages


def _format_text_output(pages: list[dict[str, Any]], total_pages: int,
                        start_page: int, max_pages: int) -> str:
    """Format extracted pages into human-readable text."""
    if not pages:
        return "No text could be extracted from the PDF."

    lines: list[str] = []
    extracted_count = len(pages)
    lines.append(f"Extracted {extracted_count} page(s) "
                 f"(pages {pages[0]['page']}-{pages[-1]['page']} of {total_pages} total):")
    lines.append("")

    for p in pages:
        lines.append(f"{'=' * 50}")
        lines.append(f"Page {p['page']}")
        lines.append(f"{'=' * 50}")
        lines.append(p["text"])
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

def tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def tool_extract_pdf_text(arguments: dict[str, Any]) -> dict[str, Any]:
    pdf_path_raw = str(arguments.get("pdf_path", "")).strip()
    if not pdf_path_raw:
        return tool_error("The pdf_path argument is required.")

    pdf_path = _resolve_path(pdf_path_raw)
    if not os.path.isfile(pdf_path):
        return tool_error(f"PDF file not found: {pdf_path_raw} (resolved: {pdf_path})")

    start_page = max(1, int(arguments.get("start_page", 1)))
    max_pages = max(0, min(int(arguments.get("max_pages", 0)), MAX_PAGES_LIMIT))

    # Try pdfplumber first, fall back to PyPDF2
    backend = ""
    try:
        pages, total_pages = _extract_with_pdfplumber(pdf_path, start_page, max_pages)
        backend = "pdfplumber"
    except ImportError:
        try:
            pages, total_pages = _extract_with_pypdf2(pdf_path, start_page, max_pages)
            backend = "PyPDF2"
        except ImportError:
            return tool_error(
                "No PDF library available. Please install one:\n"
                "  pip install pdfplumber    (recommended)\n"
                "  pip install PyPDF2        (fallback)"
            )
    except Exception as exc:
        return tool_error(f"Failed to extract PDF text: {exc}")

    text_output = _format_text_output(pages, total_pages, start_page, max_pages)

    # Compute full extracted character count
    total_chars = sum(len(p["text"]) for p in pages)

    return {
        "content": [{"type": "text", "text": text_output}],
        "structuredContent": {
            "pdf_path": pdf_path,
            "backend": backend,
            "total_pages": total_pages,
            "extracted_pages": len(pages),
            "start_page": start_page,
            "total_chars": total_chars,
            "pages": pages,
        },
        "isError": False,
    }


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
        if tool_name == "extract_pdf_text":
            send_result(request_id, tool_extract_pdf_text(arguments))
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
