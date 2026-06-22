#!/usr/bin/env python3
"""
Self-contained installer for the research-copilot self/ assets.

Run from repo root or anywhere — the script auto-detects its own directory.

What it does (idempotent):
  1. Install Python deps from self/mcp/requirements.txt (pdfplumber)
  2. Write a project-level .mcp.json that points at self/mcp/servers/
  3. Register the SessionStart hook in .claude/settings.json
  4. Regenerate skill.json metadata for every self/skills/* (required by
     Claude Code 2.1.142+ for plugin skill discovery)
  5. Verify each MCP server can start by handshaking JSON-RPC initialize
  6. Warn (without failing) if optional secrets like ARXIVSUB_SKILL_KEY are missing

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
RESEARCH_COPILOT_GUARD_SCRIPT = SELF_DIR / "hooks" / "scripts" / "research_copilot_guard.py"
SESSION_MEMORY_INJECTOR_SCRIPT = SELF_DIR / "hooks" / "scripts" / "session_start_memory_injector.py"
DISPATCH_REMINDER_SCRIPT = SELF_DIR / "hooks" / "scripts" / "user_prompt_dispatch_reminder.py"
LOOP_ARMER_SCRIPT = SELF_DIR / "hooks" / "scripts" / "post_tool_loop_armer.py"
COPILOT_WRITE_GUARD_SCRIPT = SELF_DIR / "hooks" / "scripts" / "copilot_write_guard.py"
COPILOT_SUBAGENT_STOP_SCRIPT = SELF_DIR / "hooks" / "scripts" / "copilot_subagent_stop.py"
RESEARCH_COPILOT_GUARD_PROMPT = (
    "You are the research-copilot-guard fallback, running in parallel with a "
    "primary Python guard (if Python is available). The main session acts as the "
    "research-pipeline CONDUCTOR and must DELEGATE domain work to rc-* / copilot-* "
    "sub-agents. Default to APPROVE unless you have STRONG, CONCRETE evidence "
    "that ALL of the following hold:\n\n"
    "1. This call originates from the MAIN SESSION (NOT a sub-agent). In the hook "
    "payload, a sub-agent call carries a non-empty `agent_id` field; the main "
    "session has NO `agent_id`. If `agent_id` is present, output `approve` "
    "(sub-agents run freely).\n"
    "2. The main session is doing execution-class work that must be delegated:\n"
    "   - Bash/PowerShell running an experiment script (train.py, run_experiment, "
    "wandb, mlflow, torchrun, deepspeed) that is NOT read-only inspection; OR\n"
    "   - a paper-retrieval MCP tool (mcp__arxiv-search__*, mcp__arxivsub-search__*, "
    "mcp__google-scholar__*, mcp__dblp-bib__*, mcp__research-scholar__*); OR\n"
    "   - a Write/Edit to sections/*.tex, references.bib, or "
    ".copilot/{ideas,experiments,literature}.md (but NOT .copilot/state.md or "
    ".copilot/decisions.md, which the conductor owns).\n\n"
    "If `agent_id` is present (sub-agent), or the call is read-only, or you are "
    "uncertain, output `approve`. Only when BOTH conditions above are concretely "
    "met, output `deny` with message: 'Blocked by research-copilot-guard (prompt "
    "fallback): the conductor must delegate this to an rc-* / copilot-* sub-agent.'\n\n"
    "Return the standard PreToolUse decision JSON. Be brief."
)
RESEARCH_COPILOT_GUARD_MATCHER = "Bash|PowerShell|Agent|Write|Edit|mcp__arxiv-search__.*|mcp__arxivsub-search__.*|mcp__google-scholar__.*|mcp__dblp-bib__.*|mcp__research-scholar__.*"
SKILLS_DIR = SELF_DIR / "skills"
SKILL_JSON_GENERATOR = SELF_DIR / "scripts" / "generate-skill-json.py"

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
    step("Step 1/5: install Python dependencies")
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
                # Print Python traceback to stderr if a server hangs
                # (helps diagnose socket-timeout symptoms).
                "PYTHONFAULTHANDLER": "1",
                # Avoid numpy/openblas multi-threading deadlocks on Windows
                # when MCP servers are spawned as children of Claude Code.
                "OMP_NUM_THREADS": "1",
            },
        }
    return {"mcpServers": servers}


def write_mcp_config(target: Path, dry_run: bool) -> dict[str, Any]:
    step("Step 2/5: write project .mcp.json")
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
    step("Step 3/5: register SessionStart hook in .claude/settings.json")
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


# -------- Step 3b: register PreToolUse research-copilot guard --------

def _detect_python_in_path() -> bool:
    """Whether `python` resolves in PATH at install time.

    The PreToolUse hook command uses `python ...` so it must be locatable
    by name when Claude Code spawns the hook process. `sys.executable`
    works for THIS process but the hook runs in a fresh subprocess that
    inherits the user's PATH, not ours.
    """
    return shutil.which("python") is not None or shutil.which("python3") is not None


def register_research_copilot_guard(target: Path, dry_run: bool) -> None:
    step("Step 3b/5: register research-copilot-guard PreToolUse hook")
    if not RESEARCH_COPILOT_GUARD_SCRIPT.is_file():
        warn(f"guard script missing: {RESEARCH_COPILOT_GUARD_SCRIPT}; skipping")
        return

    python_available = _detect_python_in_path()
    if python_available:
        info("Python found in PATH; registering Python command hook + prompt fallback.")
    else:
        info("Python NOT found in PATH; registering prompt-based fallback only.")

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

    hooks_root = settings.setdefault("hooks", {})
    pre_tool_use = hooks_root.setdefault("PreToolUse", [])

    # Remove any prior research-copilot-guard registrations so this is idempotent
    def _is_guard_block(block: Any) -> bool:
        if not isinstance(block, dict):
            return False
        for hk in block.get("hooks", []):
            if not isinstance(hk, dict):
                continue
            cmd = hk.get("command", "")
            prompt = hk.get("prompt", "")
            if "research_copilot_guard" in cmd or "research-copilot-guard" in prompt:
                return True
        return False

    pre_tool_use[:] = [b for b in pre_tool_use if not _is_guard_block(b)]

    hook_entries: list[dict[str, Any]] = []
    if python_available:
        guard_cmd = f'python "{RESEARCH_COPILOT_GUARD_SCRIPT.resolve()}"'.replace("\\", "/")
        hook_entries.append({
            "type": "command",
            "command": guard_cmd,
            "timeout": 10,
        })
    hook_entries.append({
        "type": "prompt",
        "prompt": RESEARCH_COPILOT_GUARD_PROMPT,
        "timeout": 15,
    })

    desired_block = {
        "matcher": RESEARCH_COPILOT_GUARD_MATCHER,
        "hooks": hook_entries,
    }
    info(f"Adding PreToolUse block (matcher: {RESEARCH_COPILOT_GUARD_MATCHER})")
    pre_tool_use.append(desired_block)

    if dry_run:
        return
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def register_copilot_write_guard(target: Path, dry_run: bool) -> None:
    step("Step 3g/5: register copilot write guard PreToolUse hook")
    if not COPILOT_WRITE_GUARD_SCRIPT.is_file():
        warn(f"copilot write guard script missing: {COPILOT_WRITE_GUARD_SCRIPT}; skipping")
        return
    settings_path, settings, valid = _load_settings(target)
    if not valid:
        return
    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])
    hook_cmd = f'python "{COPILOT_WRITE_GUARD_SCRIPT.resolve()}"'.replace("\\", "/")
    # Remove any prior copilot_write_guard registrations so reruns refresh paths
    def _is_write_guard_block(block: Any) -> bool:
        if not isinstance(block, dict):
            return False
        if block.get("matcher") != "Write|Edit":
            return False
        for hk in block.get("hooks", []):
            if not isinstance(hk, dict):
                continue
            if "copilot_write_guard.py" in hk.get("command", ""):
                return True
        return False
    pre_tool[:] = [b for b in pre_tool if not _is_write_guard_block(b)]
    pre_tool.append({
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": hook_cmd, "timeout": 10}],
    })
    if dry_run:
        return
    _save_settings(settings_path, settings)


def register_copilot_subagent_stop(target: Path, dry_run: bool) -> None:
    step("Step 3h/5: register copilot subagent stop hook")
    if not COPILOT_SUBAGENT_STOP_SCRIPT.is_file():
        warn(f"copilot subagent stop script missing: {COPILOT_SUBAGENT_STOP_SCRIPT}; skipping")
        return
    settings_path, settings, valid = _load_settings(target)
    if not valid:
        return
    hooks = settings.setdefault("hooks", {})
    stop_hooks = hooks.setdefault("SubagentStop", [])
    hook_cmd = f'python "{COPILOT_SUBAGENT_STOP_SCRIPT.resolve()}"'.replace("\\", "/")
    # Remove any prior copilot_subagent_stop registrations so reruns refresh paths
    def _is_subagent_stop_block(block: Any) -> bool:
        if not isinstance(block, dict):
            return False
        for hk in block.get("hooks", []):
            if not isinstance(hk, dict):
                continue
            if "copilot_subagent_stop.py" in hk.get("command", ""):
                return True
        return False
    stop_hooks[:] = [b for b in stop_hooks if not _is_subagent_stop_block(b)]
    stop_hooks.append({
        "hooks": [{"type": "command", "command": hook_cmd, "timeout": 10}],
    })
    if dry_run:
        return
    _save_settings(settings_path, settings)


# -------- Step 3c-3e: register the three new hooks --------

def _load_settings(target: Path) -> tuple[Path, dict, bool]:
    """Load .claude/settings.json.

    Returns (settings_path, settings_dict, json_was_valid).
    When json_was_valid is False the file existed but contained invalid JSON;
    callers should skip writing to avoid overwriting a corrupted file.
    """
    settings_dir = target / ".claude"
    settings_path = settings_dir / "settings.json"
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error(f"existing settings.json is invalid JSON ({exc}); skipping registration")
            return settings_path, {}, False
    else:
        settings = {}
    return settings_path, settings, True


def _save_settings(settings_path: Path, settings: dict) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _already_registered(blocks: list, identifier_substr: str) -> bool:
    for b in blocks:
        if not isinstance(b, dict):
            continue
        for hk in b.get("hooks", []):
            if not isinstance(hk, dict):
                continue
            if identifier_substr in (hk.get("command", "") or ""):
                return True
    return False


def _add_session_start_hook(target: Path, dry_run: bool, script: Path,
                            identifier_substr: str, timeout: int) -> None:
    settings_path, settings, valid = _load_settings(target)
    if not valid:
        return
    blocks = settings.setdefault("hooks", {}).setdefault("SessionStart", [])
    if _already_registered(blocks, identifier_substr):
        info(f"  {identifier_substr} already registered; skipping.")
        return
    cmd = f'python "{script.resolve()}"'.replace("\\", "/")
    blocks.append({
        "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]
    })
    info(f"  added SessionStart hook: {cmd}")
    if not dry_run:
        _save_settings(settings_path, settings)


def _add_user_prompt_submit_hook(target: Path, dry_run: bool, script: Path,
                                 identifier_substr: str, timeout: int) -> None:
    settings_path, settings, valid = _load_settings(target)
    if not valid:
        return
    blocks = settings.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    if _already_registered(blocks, identifier_substr):
        info(f"  {identifier_substr} already registered; skipping.")
        return
    cmd = f'python "{script.resolve()}"'.replace("\\", "/")
    blocks.append({
        "matcher": "*",
        "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]
    })
    info(f"  added UserPromptSubmit hook: {cmd}")
    if not dry_run:
        _save_settings(settings_path, settings)


def _add_post_tool_use_hook(target: Path, dry_run: bool, script: Path,
                            matcher: str, identifier_substr: str, timeout: int) -> None:
    settings_path, settings, valid = _load_settings(target)
    if not valid:
        return
    blocks = settings.setdefault("hooks", {}).setdefault("PostToolUse", [])
    if _already_registered(blocks, identifier_substr):
        info(f"  {identifier_substr} already registered; skipping.")
        return
    cmd = f'python "{script.resolve()}"'.replace("\\", "/")
    blocks.append({
        "matcher": matcher,
        "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]
    })
    info(f"  added PostToolUse hook ({matcher}): {cmd}")
    if not dry_run:
        _save_settings(settings_path, settings)


def register_session_memory_injector(target: Path, dry_run: bool) -> None:
    step("Step 3c/5: register SessionStart memory injector hook")
    if not SESSION_MEMORY_INJECTOR_SCRIPT.is_file():
        warn(f"injector script missing: {SESSION_MEMORY_INJECTOR_SCRIPT}; skipping")
        return
    _add_session_start_hook(
        target=target,
        dry_run=dry_run,
        script=SESSION_MEMORY_INJECTOR_SCRIPT,
        identifier_substr="session_start_memory_injector.py",
        timeout=10,
    )


def register_dispatch_reminder(target: Path, dry_run: bool) -> None:
    step("Step 3d/5: register UserPromptSubmit dispatch-reminder hook")
    if not DISPATCH_REMINDER_SCRIPT.is_file():
        warn(f"reminder script missing: {DISPATCH_REMINDER_SCRIPT}; skipping")
        return
    _add_user_prompt_submit_hook(
        target=target,
        dry_run=dry_run,
        script=DISPATCH_REMINDER_SCRIPT,
        identifier_substr="user_prompt_dispatch_reminder.py",
        timeout=5,
    )


def register_loop_armer(target: Path, dry_run: bool) -> None:
    step("Step 3e/5: register PostToolUse loop-armer hook")
    if not LOOP_ARMER_SCRIPT.is_file():
        warn(f"loop-armer script missing: {LOOP_ARMER_SCRIPT}; skipping")
        return
    _add_post_tool_use_hook(
        target=target,
        dry_run=dry_run,
        script=LOOP_ARMER_SCRIPT,
        matcher="Bash",
        identifier_substr="post_tool_loop_armer.py",
        timeout=5,
    )


def register_conductor_agent(target: Path, dry_run: bool) -> None:
    """Set 'agent': 'copilot-conductor' in .claude/settings.json so the main
    session loads the conductor's system prompt at highest priority."""
    step("Step 3f/5: register copilot-conductor as main-session agent")
    settings_path, settings, valid = _load_settings(target)
    if not valid:
        return
    if settings.get("agent") == "copilot-conductor":
        info("agent key already set to copilot-conductor; skipping.")
        return
    info("Setting agent key to 'copilot-conductor'")
    settings["agent"] = "copilot-conductor"
    if dry_run:
        return
    _save_settings(settings_path, settings)


# -------- Step 4: regenerate skill.json metadata --------

def regenerate_skill_jsons(dry_run: bool) -> bool:
    """Run self/scripts/generate-skill-json.py to ensure every skill has a
    skill.json sibling (required by Claude Code 2.1.142+)."""
    step("Step 4/5: regenerate skill.json metadata for self/skills/*")
    if not SKILL_JSON_GENERATOR.is_file():
        warn(f"missing generator: {SKILL_JSON_GENERATOR}; skipping")
        return True
    if not SKILLS_DIR.is_dir():
        warn(f"missing skills dir: {SKILLS_DIR}; skipping")
        return True
    cmd = [sys.executable, str(SKILL_JSON_GENERATOR), "--root", str(SKILLS_DIR)]
    info("Plan: " + " ".join(cmd))
    if dry_run:
        return True
    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError as exc:
        error(f"failed to spawn generator: {exc}")
        return False
    if result.returncode != 0:
        warn(f"generator exited with {result.returncode}; skills may not be discoverable")
        return False
    return True


# -------- Step 5: verify each MCP server starts --------

def verify_mcp_servers(config: dict[str, Any]) -> dict[str, str]:
    step("Step 5/5: verify each MCP server initializes")
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


# -------- Step 0: dependency marketplaces --------

DEPENDENCY_MARKETPLACES = [
    ("academic-research-skills", "Imbad0202/academic-research-skills"),
    ("paper-polish-workflow", "Lylll9436/Paper-Polish-Workflow-skill"),
    ("andrej-karpathy-skills", "multica-ai/andrej-karpathy-skills"),
    ("example-skills", "anthropics/skills"),
    ("ml-paper-writing / autoresearch", "Orchestra-Research/AI-Research-SKILLs"),
]


def report_dependency_marketplaces() -> None:
    step("Prerequisite: add dependency marketplaces")
    warn("This plugin depends on skills from 5 third-party marketplaces.")
    warn("The superpowers dependency uses Claude Code's built-in claude-plugins-official marketplace.")
    warn("If you haven't added them, plugin dependencies will stay unresolved.")
    print()
    print("  Run these commands in Claude Code before installing the plugin:")
    print()
    for _label, repo in DEPENDENCY_MARKETPLACES:
        print(f"    /plugin marketplace add {repo}")
    print()


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

    report_dependency_marketplaces()

    if not args.skip_deps:
        if not install_python_deps(args.dry_run):
            return 1

    config = write_mcp_config(target, args.dry_run)
    register_hook(target, args.dry_run)
    register_research_copilot_guard(target, args.dry_run)
    register_session_memory_injector(target, args.dry_run)
    register_dispatch_reminder(target, args.dry_run)
    register_loop_armer(target, args.dry_run)
    register_conductor_agent(target, args.dry_run)
    register_copilot_write_guard(target, args.dry_run)
    register_copilot_subagent_stop(target, args.dry_run)
    regenerate_skill_jsons(args.dry_run)

    if not args.skip_verify and not args.dry_run:
        verify_mcp_servers(config)

    report_optional_secrets()

    print()
    info("Install complete.")
    info("Next steps:")
    print("  1. Restart Claude Code (or run /clear) to pick up new MCP servers")
    print("  2. The main session is now the pipeline conductor — just state your goal")
    print("     (e.g. 'where does this research stand?'); it will plan and delegate.")
    print("  3. Call a sub-agent directly: @copilot-literature / @copilot-ideation / @copilot-experiment / @copilot-writer / @copilot-polisher / @copilot-reviewer / @copilot-rebuttal")
    print("  4. Diagnose MCP latency: python self/scripts/diagnose-mcp.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
