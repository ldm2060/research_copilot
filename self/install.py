#!/usr/bin/env python3
"""
Self-contained installer for the research-copilot self/ assets.

Run from repo root or anywhere — the script auto-detects its own directory.

What it does (idempotent):
  1. Install Python deps from self/mcp/requirements.txt (pdfplumber)
  2. Write a project-level .mcp.json that points at self/mcp/servers/
  3. Register the SessionStart hook in .claude/settings.json
  4. Verify each MCP server can start by handshaking JSON-RPC initialize
  5. Warn (without failing) if optional secrets like ARXIVSUB_SKILL_KEY are missing

Usage:
  python self/install.py                 # full install at repo root
  python self/install.py --target /path  # install into a different workspace
  python self/install.py --dry-run       # show planned actions without writing
  python self/install.py --skip-deps     # skip pip install
  python self/install.py --skip-verify   # skip MCP handshake test
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SELF_DIR = Path(__file__).resolve().parent
REPO_ROOT = SELF_DIR.parent
MCP_SOURCE_DIR = SELF_DIR / "mcp"
MCP_SERVERS_DIR = MCP_SOURCE_DIR / "servers"
MCP_REQUIREMENTS = MCP_SOURCE_DIR / "requirements.txt"
HOOK_SCRIPT = SELF_DIR / "hooks" / "scripts" / "scientist_guardrails.py"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def color(text: str, c: str) -> str:
    if not sys.stdout.isatty() or os.name == "nt" and not os.environ.get("WT_SESSION"):
        return text
    return f"{c}{text}{RESET}"


def info(msg: str) -> None:
    print(color("[info]", GREEN) + " " + msg)


def warn(msg: str) -> None:
    print(color("[warn]", YELLOW) + " " + msg)


def error(msg: str) -> None:
    print(color("[error]", RED) + " " + msg, file=sys.stderr)


def step(msg: str) -> None:
    print()
    print(color(f"==> {msg}", BOLD))


# -------- Step 1: install Python deps --------

def install_python_deps(dry_run: bool) -> bool:
    step("Step 1/4: install Python dependencies")
    if not MCP_REQUIREMENTS.is_file():
        warn(f"requirements file not found: {MCP_REQUIREMENTS}; skipping")
        return True
    info(f"Reading {MCP_REQUIREMENTS}")
    deps = [
        line.strip() for line in MCP_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not deps:
        info("No deps declared. Skipping.")
        return True
    cmd = [sys.executable, "-m", "pip", "install", *deps]
    info("Plan: " + " ".join(cmd))
    if dry_run:
        return True
    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError:
        error("pip not available on this Python. Install pip first.")
        return False
    if result.returncode != 0:
        warn(f"pip exited with {result.returncode}; checking pdfplumber by import...")
        try:
            import pdfplumber  # noqa: F401
            info("pdfplumber importable; continuing.")
            return True
        except ImportError:
            warn("pdfplumber not importable; pdf-text MCP will fall back to PyPDF2 if installed.")
            return True
    info("Python deps OK.")
    return True


# -------- Step 2: write project .mcp.json --------

def build_mcp_config(target: Path) -> dict[str, Any]:
    """
    Generate a Claude-Code-style .mcp.json that points at the *current* self/mcp/servers/ tree.

    We use absolute paths instead of ${workspaceFolder} so that the file works whether or not
    the workspace var is expanded by the host.
    """
    servers: dict[str, Any] = {}
    if not MCP_SERVERS_DIR.is_dir():
        warn(f"No servers directory at {MCP_SERVERS_DIR}; emitting empty mcp config")
        return {"mcpServers": servers}

    for child in sorted(MCP_SERVERS_DIR.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        server_py = child / "server.py"
        if not server_py.is_file():
            continue
        servers[child.name] = {
            "type": "stdio",
            "command": "python",
            "args": ["-u", str(server_py.resolve()).replace("\\", "/")],
            "env": {
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
                "PYTHONUNBUFFERED": "1",
            },
        }
    return {"mcpServers": servers}


def write_mcp_config(target: Path, dry_run: bool) -> dict[str, Any]:
    step("Step 2/4: write project .mcp.json")
    config = build_mcp_config(target)
    out_path = target / ".mcp.json"
    info(f"Writing {len(config['mcpServers'])} servers to {out_path}")
    for name in config["mcpServers"]:
        print(f"  - {name}")
    if dry_run:
        return config
    out_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return config


# -------- Step 3: register SessionStart hook --------

def register_hook(target: Path, dry_run: bool) -> None:
    step("Step 3/4: register SessionStart hook in .claude/settings.json")
    if not HOOK_SCRIPT.is_file():
        warn(f"hook script missing: {HOOK_SCRIPT}; skipping hook registration")
        return

    settings_dir = target / ".claude"
    settings_path = settings_dir / "settings.json"
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error(f"existing settings.json is invalid JSON ({exc}); aborting hook registration")
            return
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    session_start = hooks.setdefault("SessionStart", [])

    hook_cmd = f'python "{HOOK_SCRIPT.resolve()}"'.replace("\\", "/")
    desired_block = {
        "hooks": [
            {
                "type": "command",
                "command": hook_cmd,
                "timeout": 10,
            }
        ]
    }

    # idempotency: don't add duplicate
    already_present = False
    for block in session_start:
        for hk in block.get("hooks", []) if isinstance(block, dict) else []:
            cmd = hk.get("command", "") if isinstance(hk, dict) else ""
            if "scientist_guardrails.py" in cmd:
                already_present = True
                break
    if already_present:
        info("Hook already registered; skipping.")
        return

    info(f"Adding hook block: {hook_cmd}")
    session_start.append(desired_block)

    if dry_run:
        return
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# -------- Step 4: verify each MCP server starts --------

def verify_mcp_servers(config: dict[str, Any]) -> dict[str, str]:
    step("Step 4/4: verify each MCP server initializes")
    results: dict[str, str] = {}
    initialize_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "self-installer", "version": "0.1.0"},
        },
    }
    request = (json.dumps(initialize_payload) + "\n").encode("utf-8")

    for name, srv in config.get("mcpServers", {}).items():
        cmd = [srv["command"], *srv["args"]]
        env = {**os.environ, **srv.get("env", {})}
        try:
            proc = subprocess.run(
                cmd,
                input=request,
                capture_output=True,
                env=env,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            results[name] = f"FAIL ({type(exc).__name__})"
            warn(f"  {name}: {results[name]}")
            continue
        # Look for a JSON-RPC response in stdout (servers may print initialize result and exit on EOF)
        stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        ok = '"jsonrpc"' in stdout and ('"result"' in stdout or '"id":1' in stdout or '"id": 1' in stdout)
        results[name] = "OK" if ok else f"FAIL (rc={proc.returncode})"
        if ok:
            info(f"  {name}: OK")
        else:
            warn(f"  {name}: {results[name]}")
            if proc.stderr:
                tail = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()[-3:]
                for line in tail:
                    print(f"    stderr: {line}")
    return results


# -------- Step 5: optional secrets --------

def report_optional_secrets() -> None:
    step("Optional: API keys")
    arxivsub = os.environ.get("ARXIVSUB_SKILL_KEY")
    if arxivsub:
        info("ARXIVSUB_SKILL_KEY detected in environment")
    else:
        warn("ARXIVSUB_SKILL_KEY not set — arxivsub-search MCP will refuse to call.")
        warn("  To enable, get a key from the arXivSub website and either:")
        warn("    export ARXIVSUB_SKILL_KEY=your_key_here       # bash/zsh")
        warn("    setx ARXIVSUB_SKILL_KEY your_key_here          # Windows persistent")
        warn("  or add to a .env file at the repo root: ARXIVSUB_SKILL_KEY=your_key_here")


# -------- main --------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=str(REPO_ROOT),
                        help="Workspace root to install into (default: repo root containing self/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print actions without writing files")
    parser.add_argument("--skip-deps", action="store_true",
                        help="Skip pip install step")
    parser.add_argument("--skip-verify", action="store_true",
                        help="Skip MCP server handshake test")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = Path(args.target).resolve()

    print(color("Research Copilot installer", BOLD))
    print(f"  self dir : {SELF_DIR}")
    print(f"  target   : {target}")
    print(f"  dry-run  : {args.dry_run}")

    if not args.skip_deps:
        if not install_python_deps(args.dry_run):
            return 1

    config = write_mcp_config(target, args.dry_run)
    register_hook(target, args.dry_run)

    if not args.skip_verify and not args.dry_run:
        verify_mcp_servers(config)

    report_optional_secrets()

    print()
    info("Install complete.")
    info("Next steps:")
    print("  1. Restart Claude Code (or run /clear) to pick up new MCP servers")
    print("  2. Try: @paper '看看这篇论文当前状态'")
    print("  3. Try: @scientist 'check runtime'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
