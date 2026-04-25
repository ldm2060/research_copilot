"""AI Scientist MCP server.

This server intentionally exposes only non-model operational utilities.
The scientist-support skill bundle retains only static runtime assets and
experiment directories rather than executable model scripts. Model-driven stages such as ideation,
experiment search, plotting, writeup, and review are executed as scientist
agent tasks rather than via MCP.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Force binary unbuffered I/O on Windows pipes.
if sys.platform == "win32":
    import msvcrt

    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


SERVER_NAME = "ai-scientist"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {
        "name": "validate_runtime",
        "title": "Validate AI Scientist Runtime",
        "description": "Check whether the scientist-support AI Scientist runtime root is present and whether Python, LaTeX, poppler, and CUDA prerequisites are available.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Optional override for the AI Scientist runtime root. If omitted, the server locates the scientist-support skill runtime.",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "list_experiments",
        "title": "List AI Scientist Experiments",
        "description": "List recent experiment folders under the scientist-support AI Scientist runtime experiments directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "inspect_experiment",
        "title": "Inspect AI Scientist Experiment",
        "description": "Inspect one AI Scientist experiment folder and summarize key non-model artifacts such as PDFs, logs, LaTeX inputs, citations progress, and token tracking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "experiment_name": {
                    "type": "string",
                    "description": "Experiment directory name under the runtime experiments folder.",
                },
                "experiment_path": {
                    "type": "string",
                    "description": "Optional absolute or project-relative path to an experiment directory.",
                },
                "log_tail_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 200,
                    "default": 40,
                    "description": "Number of lines to include from the newest log file, if any.",
                },
            },
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


def tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def discover_ai_scientist_root(project_root: str | None = None) -> Path:
    if project_root:
        root = Path(project_root).expanduser()
        if not root.is_absolute():
            root = (Path.cwd() / root).resolve()
        else:
            root = root.resolve()
        return root

    candidates: list[Path] = []
    seen: set[str] = set()
    for base in [Path.cwd(), *Path(__file__).resolve().parents]:
        for candidate in [
            base / ".github" / "skills" / "scientist-support" / "runtime",
            base / "self" / "skills" / "scientist-support" / "runtime",
        ]:
            key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()

    raise FileNotFoundError("Could not discover the scientist-support skill runtime. Pass project_root explicitly if you intentionally moved it.")


def make_text_result(text: str, structured: dict[str, Any] | None = None, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }
    if structured is not None:
        result["structuredContent"] = structured
    return result


def tail_text(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def tail_lines(path: Path, max_lines: int) -> str:
    if max_lines <= 0 or not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return "\n".join(text.splitlines()[-max_lines:])


def load_json_file(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def tool_validate_runtime(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        ai_root = discover_ai_scientist_root(arguments.get("project_root"))
    except FileNotFoundError as exc:
        return tool_error(str(exc))

    python_executable = sys.executable or shutil.which("python") or "python"
    binaries = {
        "pdflatex": shutil.which("pdflatex"),
        "bibtex": shutil.which("bibtex"),
        "pdftotext": shutil.which("pdftotext"),
        "chktex": shutil.which("chktex"),
        "nvidia-smi": shutil.which("nvidia-smi"),
    }

    torch_probe = subprocess.run(
        [
            python_executable,
            "-c",
            "import json, torch; print(json.dumps({'cuda_available': bool(torch.cuda.is_available()), 'device_count': int(torch.cuda.device_count())}))",
        ],
        cwd=str(ai_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    torch_info: dict[str, Any]
    if torch_probe.returncode == 0:
        try:
            torch_info = json.loads(torch_probe.stdout.strip())
        except json.JSONDecodeError:
            torch_info = {"cuda_available": False, "device_count": 0, "raw": torch_probe.stdout.strip()}
    else:
        torch_info = {
            "cuda_available": False,
            "device_count": 0,
            "error": tail_text(torch_probe.stderr.strip() or torch_probe.stdout.strip()),
        }

    checks = {
        "ai_scientist_root": str(ai_root),
        "python": python_executable,
        "python_exists": Path(python_executable).exists() if python_executable != "python" else True,
        "torch_importable": torch_probe.returncode == 0,
        "latex_binaries": {name: bool(path) for name, path in binaries.items()},
        "torch": torch_info,
        "platform": sys.platform,
    }

    ready = (
        checks["torch_importable"]
        and bool(binaries["pdflatex"])
        and bool(binaries["bibtex"])
    )
    lines = [
        f"Skill runtime root: {ai_root}",
        f"Python: {python_executable}",
        f"Platform: {sys.platform}",
        "",
        "Binaries:",
    ]
    for name, path in binaries.items():
        lines.append(f"- {name}: {'OK' if path else 'MISSING'}{f' ({path})' if path else ''}")
    lines.extend(
        [
            "",
            f"torch importable: {checks['torch_importable']}",
            f"CUDA available: {torch_info.get('cuda_available', False)}",
            f"CUDA device count: {torch_info.get('device_count', 0)}",
            "",
            f"Ready for local bundle workflow: {ready}",
        ]
    )
    lines.append("Note: MCP validate_runtime only checks non-model host prerequisites for the Copilot bundle.")
    if sys.platform != "linux":
        lines.append("Risk: some downstream experiment code may still assume Linux + CUDA even though bundle-side model scripts are disabled.")
    lines.extend(
        [
            "",
            "Agent-owned model tasks:",
            "- ideation: use the scientist-ideation skill or scientist agent directly in Copilot",
            "- experiment: use the scientist-experiment-runner skill or scientist agent directly in Copilot",
            "- plotting: use the scientist-plotting skill or scientist agent directly in Copilot",
            "- writeup: use the scientist-writeup skill or scientist agent directly in Copilot",
            "- review: use the scientist-review skill or scientist agent directly in Copilot",
        ]
    )
    return make_text_result("\n".join(lines), {"ready": ready, **checks}, is_error=False)


def list_experiment_dirs(ai_root: Path) -> list[Path]:
    experiments_root = ai_root / "experiments"
    if not experiments_root.exists():
        return []
    return sorted((path for path in experiments_root.iterdir() if path.is_dir()), key=lambda path: path.stat().st_mtime, reverse=True)


def resolve_experiment_dir(ai_root: Path, arguments: dict[str, Any]) -> Path:
    experiment_path = arguments.get("experiment_path")
    if experiment_path:
        resolved = Path(experiment_path).expanduser()
        if not resolved.is_absolute():
            resolved = (Path.cwd() / resolved).resolve()
        else:
            resolved = resolved.resolve()
        return resolved

    experiment_name = arguments.get("experiment_name")
    if experiment_name:
        return (ai_root / "experiments" / experiment_name).resolve()

    raise ValueError("Pass either experiment_name or experiment_path.")


def tool_list_experiments(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        ai_root = discover_ai_scientist_root(arguments.get("project_root"))
    except FileNotFoundError as exc:
        return tool_error(str(exc))

    limit = int(arguments.get("limit", 10))
    items = []
    for path in list_experiment_dirs(ai_root)[:limit]:
        pdfs = sorted(path.glob("*.pdf"))
        items.append(
            {
                "name": path.name,
                "path": str(path),
                "pdf_count": len(pdfs),
                "latest_pdf": str(pdfs[-1]) if pdfs else None,
            }
        )

    if not items:
        return make_text_result("No experiment folders found.", {"experiments": []}, is_error=False)

    lines = ["Recent AI Scientist experiments:", ""]
    for idx, item in enumerate(items, start=1):
        lines.append(f"[{idx}] {item['name']}")
        lines.append(f"  Path      : {item['path']}")
        lines.append(f"  PDF count : {item['pdf_count']}")
        if item["latest_pdf"]:
            lines.append(f"  Latest PDF: {item['latest_pdf']}")
        lines.append("")
    return make_text_result("\n".join(lines).strip(), {"experiments": items}, is_error=False)


def tool_inspect_experiment(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        ai_root = discover_ai_scientist_root(arguments.get("project_root"))
        experiment_dir = resolve_experiment_dir(ai_root, arguments)
    except (FileNotFoundError, ValueError) as exc:
        return tool_error(str(exc))

    if not experiment_dir.exists() or not experiment_dir.is_dir():
        return tool_error(f"Experiment directory not found: {experiment_dir}")

    log_tail_lines = int(arguments.get("log_tail_lines", 40))
    pdfs = sorted(experiment_dir.glob("*.pdf"))
    json_files = sorted(experiment_dir.glob("*.json"))
    logs_dir = experiment_dir / "logs"
    latex_dir = experiment_dir / "latex"
    latest_log: Path | None = None
    if logs_dir.exists():
        log_candidates = sorted((path for path in logs_dir.rglob("*") if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
        if log_candidates:
            latest_log = log_candidates[0]

    token_tracker_summary = load_json_file(experiment_dir / "token_tracker.json")
    citations_progress = load_json_file(experiment_dir / "citations_progress.json")
    structured = {
        "name": experiment_dir.name,
        "path": str(experiment_dir),
        "files": {
            "idea_md": str(experiment_dir / "idea.md") if (experiment_dir / "idea.md").exists() else None,
            "idea_json": str(experiment_dir / "idea.json") if (experiment_dir / "idea.json").exists() else None,
            "cached_citations_bib": str(experiment_dir / "cached_citations.bib") if (experiment_dir / "cached_citations.bib").exists() else None,
            "token_tracker_json": str(experiment_dir / "token_tracker.json") if (experiment_dir / "token_tracker.json").exists() else None,
            "citations_progress_json": str(experiment_dir / "citations_progress.json") if (experiment_dir / "citations_progress.json").exists() else None,
        },
        "pdfs": [str(path) for path in pdfs],
        "top_level_json_files": [str(path) for path in json_files],
        "latex": {
            "dir": str(latex_dir) if latex_dir.exists() else None,
            "template_tex": str(latex_dir / "template.tex") if (latex_dir / "template.tex").exists() else None,
        },
        "logs": {
            "dir": str(logs_dir) if logs_dir.exists() else None,
            "latest_log": str(latest_log) if latest_log else None,
            "latest_log_tail": tail_lines(latest_log, log_tail_lines) if latest_log else "",
        },
        "token_tracker_summary": token_tracker_summary,
        "citations_progress": citations_progress,
    }

    lines = [
        f"Experiment: {experiment_dir.name}",
        f"Path: {experiment_dir}",
        f"PDFs: {len(pdfs)}",
        f"Top-level JSON files: {len(json_files)}",
        f"Latex template present: {(latex_dir / 'template.tex').exists()}",
        f"Token tracker present: {(experiment_dir / 'token_tracker.json').exists()}",
        f"Citations progress present: {(experiment_dir / 'citations_progress.json').exists()}",
    ]
    if latest_log:
        lines.extend(["", f"Latest log: {latest_log}"])
        log_tail = structured["logs"]["latest_log_tail"]
        if log_tail:
            lines.extend(["", "Latest log tail:", log_tail])
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
        tool_map = {
            "validate_runtime": tool_validate_runtime,
            "list_experiments": tool_list_experiments,
            "inspect_experiment": tool_inspect_experiment,
        }
        tool = tool_map.get(tool_name)
        if tool is None:
            send_error(request_id, -32602, f"Unknown tool: {tool_name}")
            return
        try:
            send_result(request_id, tool(arguments))
        except Exception as exc:
            send_result(request_id, tool_error(f"Tool {tool_name} failed: {exc}"))
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
            request_id = message.get("id")
            if request_id is not None:
                send_error(request_id, -32000, f"Internal error: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())