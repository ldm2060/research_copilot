#!/usr/bin/env python3
"""
Diagnose MCP servers configured in project .mcp.json.

Per-server checks:
  1. initialize handshake time (cold start)
  2. tools/list time
  3. (optional) a sample call duration if a probe is registered
  4. tail of stderr if anything went wrong

Why this exists:
  Symptoms like "socket 超时" / hangs in agent calls are often caused by
  one specific MCP server being slow, or its stdio pipe deadlocking on
  Windows. Running this script in isolation tells you which server is
  the culprit, without paying the cost of going through Claude Code.

Usage:
  python self/scripts/diagnose-mcp.py                  # 测全部
  python self/scripts/diagnose-mcp.py arxiv-search     # 只测一个
  python self/scripts/diagnose-mcp.py --watch          # 持续监控（每 60s 一轮）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_CONFIG = REPO_ROOT / ".mcp.json"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def color(text: str, c: str) -> str:
    if not sys.stdout.isatty() or (os.name == "nt" and not os.environ.get("WT_SESSION")):
        return text
    return f"{c}{text}{RESET}"


def fmt_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    return f"{seconds / 60:.1f}min"


def time_label(seconds: float, *, ok: float, warn: float) -> str:
    if seconds < ok:
        return color(f"{fmt_time(seconds)} ✅", GREEN)
    if seconds < warn:
        return color(f"{fmt_time(seconds)} ⚠️", YELLOW)
    return color(f"{fmt_time(seconds)} ❌", RED)


def load_config() -> dict[str, Any]:
    if not MCP_CONFIG.is_file():
        print(color(f"[error] .mcp.json not found at {MCP_CONFIG}", RED), file=sys.stderr)
        print("       Run: python self/install.py", file=sys.stderr)
        sys.exit(2)
    return json.loads(MCP_CONFIG.read_text(encoding="utf-8"))


def run_probe(server_name: str, server_cfg: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    """Run a 2-step JSON-RPC probe: initialize → tools/list."""
    cmd = [server_cfg["command"], *server_cfg.get("args", [])]
    env = {**os.environ, **server_cfg.get("env", {})}

    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "diagnose-mcp", "version": "0.1.0"},
        },
    }
    list_payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    request = (
        json.dumps(init_payload) + "\n" + json.dumps(list_payload) + "\n"
    ).encode("utf-8")

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            input=request,
            capture_output=True,
            env=env,
            timeout=timeout,
        )
        elapsed = time.monotonic() - t0
        stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""

        # Try to detect that we actually got the two responses
        init_ok = '"id":1' in stdout.replace(" ", "") or '"id": 1' in stdout
        list_ok = '"id":2' in stdout.replace(" ", "") or '"id": 2' in stdout

        # Best-effort: count how many tools the server offers
        tools_count = stdout.count('"name":') if list_ok else 0

        return {
            "ok": init_ok and list_ok,
            "elapsed": elapsed,
            "init_ok": init_ok,
            "list_ok": list_ok,
            "tools_count": tools_count,
            "rc": proc.returncode,
            "stderr_tail": "\n".join(stderr.strip().splitlines()[-5:]),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "elapsed": float(timeout), "error": "timeout"}
    except FileNotFoundError as exc:
        return {"ok": False, "elapsed": 0.0, "error": f"FileNotFoundError: {exc}"}


def diagnose_one(name: str, cfg: dict[str, Any]) -> bool:
    print(color(f"\n=== {name} ===", BOLD))
    cmd_str = " ".join([cfg["command"], *cfg.get("args", [])])
    print(f"  cmd: {cmd_str}")
    result = run_probe(name, cfg)
    if result.get("error") == "timeout":
        print(color(f"  ❌ TIMEOUT after 30s — server hung", RED))
        return False
    if not result.get("ok"):
        print(color(f"  ❌ FAIL (rc={result.get('rc', '?')})", RED))
        if result.get("stderr_tail"):
            print(color("  stderr (last 5 lines):", YELLOW))
            for line in result["stderr_tail"].splitlines():
                print(f"    {line}")
        return False
    elapsed = result["elapsed"]
    label = time_label(elapsed, ok=2.0, warn=8.0)
    print(f"  initialize+tools/list: {label}")
    print(f"  tools count: {result['tools_count']}")
    if result.get("stderr_tail"):
        # Even successful runs may emit warnings to stderr
        print(color("  stderr (informational):", YELLOW))
        for line in result["stderr_tail"].splitlines():
            print(f"    {line}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("server", nargs="?", help="只测一个 server（不传则全部测）")
    parser.add_argument("--watch", action="store_true", help="持续监控，每 60s 一轮")
    args = parser.parse_args()

    config = load_config()
    servers: dict[str, Any] = config.get("mcpServers", {})
    if not servers:
        print(color("[warn] no MCP servers configured in .mcp.json", YELLOW))
        return 1

    if args.server:
        if args.server not in servers:
            print(color(f"[error] unknown server: {args.server}", RED), file=sys.stderr)
            print(f"available: {', '.join(servers)}", file=sys.stderr)
            return 2
        targets = {args.server: servers[args.server]}
    else:
        targets = servers

    while True:
        print(color(f"\n[diagnose-mcp] {time.strftime('%Y-%m-%d %H:%M:%S')} — testing {len(targets)} server(s)", BOLD))
        all_ok = True
        for name, cfg in targets.items():
            ok = diagnose_one(name, cfg)
            all_ok = all_ok and ok
        print(color("\nSummary:", BOLD))
        if all_ok:
            print(color("  All servers responded ✅", GREEN))
        else:
            print(color("  Some servers failed — see details above ❌", RED))
            print("  Tips:")
            print("    - 启动慢: 服务器首次加载重型库（pdfplumber 等）")
            print("    - 卡死: 检查 Windows 任务管理器是否有僵尸 python.exe")
            print("    - rc != 0: stderr 末尾几行通常会指出原因")
        if not args.watch:
            return 0 if all_ok else 1
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
