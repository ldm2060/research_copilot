"""SessionStart hook: inject .copilot/ __HANDOFF__ summaries into context."""
from __future__ import annotations

import json
from pathlib import Path
import sys

HANDOFF_HEADER = "## __HANDOFF__"
COPILOT_FILES = ["state.md", "literature.md", "ideas.md",
                 "experiments.md", "decisions.md", "handoff.md"]
MAX_TOTAL_LINES = 400
PIPELINES_TAIL_LINES = 20
RECENT_PIPELINES = 3


def extract_handoff_block(text: str) -> str | None:
    """Return the body of the trailing ## __HANDOFF__ section, or None."""
    idx = text.rfind(HANDOFF_HEADER)
    if idx < 0:
        return None
    body = text[idx + len(HANDOFF_HEADER):].strip()
    end = body.find("\n## ")
    if end >= 0:
        body = body[:end].rstrip()
    return body or None


def extract_last_n_lines(text: str, n: int) -> str:
    lines = text.rstrip("\n").split("\n")
    return "\n".join(lines[-n:])


def main() -> int:
    workspace = Path.cwd()
    copilot = workspace / ".copilot"
    if not copilot.exists():
        sys.stdout.write("[memory-injector] .copilot/ not initialized — skipping.\n")
        sys.stdout.flush()
        return 0

    blocks: list[str] = []
    total_lines = 0

    for fname in COPILOT_FILES:
        f = copilot / fname
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        block = extract_handoff_block(text)
        if block is None:
            block = extract_last_n_lines(text, n=PIPELINES_TAIL_LINES)
            if not block.strip():
                continue
            header = f"### {fname} (no __HANDOFF__; last {PIPELINES_TAIL_LINES} lines)"
        else:
            header = f"### {fname}"
        blocks.append(f"{header}\n{block}")
        total_lines += block.count("\n") + 2
        if total_lines >= MAX_TOTAL_LINES:
            blocks.append(f"[memory-injector] truncated at {MAX_TOTAL_LINES} lines budget")
            break

    # ---- Write last_updated snapshot for SubagentStop hook ----
    snapshot: dict[str, str | None] = {}
    for fname in COPILOT_FILES:
        f = copilot / fname
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        idx = text.rfind(HANDOFF_HEADER)
        if idx < 0:
            snapshot[fname] = None
            continue
        body = text[idx + len(HANDOFF_HEADER):]
        last_updated: str | None = None
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("- last_updated:"):
                last_updated = s.split(":", 1)[1].strip() or None
                break
        snapshot[fname] = last_updated
    try:
        (copilot / ".session_snapshot.json").write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    pipelines_dir = copilot / "pipelines"
    if pipelines_dir.is_dir() and total_lines < MAX_TOTAL_LINES:
        recent = sorted(pipelines_dir.glob("*.md"))[-RECENT_PIPELINES:]
        for p in recent:
            text = p.read_text(encoding="utf-8", errors="replace")
            block = extract_handoff_block(text) or extract_last_n_lines(text, n=PIPELINES_TAIL_LINES)
            if not block.strip():
                continue
            blocks.append(f"### pipelines/{p.stem}\n{block}")
            total_lines += block.count("\n") + 2
            if total_lines >= MAX_TOTAL_LINES:
                break

    if not blocks:
        sys.stdout.write(
            "[memory-injector] .copilot/ exists but no __HANDOFF__ blocks found — "
            "sub-agents likely not following PIPELINE-OS §9.\n"
        )
        sys.stdout.flush()
        return 0

    sys.stdout.write("[memory-injector] Loaded research state from .copilot/:\n\n")
    sys.stdout.write("\n\n".join(blocks))
    sys.stdout.write(
        "\n\n[memory-injector] Constraints: do NOT propose ideas already in ideas.md; "
        "do NOT re-run experiments already in experiments.md unless explicitly asked.\n"
    )
    sys.stdout.flush()

    # ---- Summarize last 24h of violations log ----
    vlog = copilot / "__violations.log"
    if vlog.is_file():
        try:
            import datetime as _dt
            now = _dt.datetime.now(_dt.timezone.utc)
            cutoff = now - _dt.timedelta(hours=24)
            hard_blocks = 0
            releases = 0
            soft_warns = 0
            for line in vlog.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    t = _dt.datetime.fromisoformat(rec.get("ts", "").replace("Z", "+00:00"))
                except ValueError:
                    continue
                if t.tzinfo is None:
                    t = t.replace(tzinfo=_dt.timezone.utc)
                if t < cutoff:
                    continue
                sev, kind = rec.get("sev"), rec.get("kind")
                if sev == "HARD" and kind == "BLOCK":
                    hard_blocks += 1
                elif sev == "HARD" and kind == "RELEASE":
                    releases += 1
                elif sev == "SOFT" and kind == "WARN":
                    soft_warns += 1
            if hard_blocks or releases or soft_warns:
                sys.stdout.write(
                    f"\n[memory-injector] Last 24h: {hard_blocks} HARD blocks "
                    f"({releases} 3-strike releases), {soft_warns} SOFT warns. "
                    f"See .copilot/__violations.log.\n"
                )
                sys.stdout.flush()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
