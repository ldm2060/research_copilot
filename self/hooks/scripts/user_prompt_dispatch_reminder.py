"""UserPromptSubmit hook: when the prompt looks like an execution task,
inject a one-screen reminder to dispatch a sub-agent instead of inlining."""
from __future__ import annotations

import sys
from pathlib import Path

ALLOWLIST_PREFIXES = ("/", "@")
ALLOWLIST_PHRASES = (
    "what's next", "what is next", "下一步", "状态", "看一下", "看看",
    "show me", "ls ", "cat ", "tell me about", "explain",
)
EXEC_KEYWORDS = (
    "搜", "查", "文献", "paper", "arxiv", "scholar", "citation",
    "brainstorm", "头脑风暴", "创新", "idea", "ideation",
    "跑", "训练", "实验", "ablation", "baseline", "复现", "train", "experiment",
    "写", "draft", "polish", "expand", "shorten", "translate", "caption",
    "review", "审稿", "rebuttal", "反驳", "sanity",
    "pdf", "读 ", "read the paper",
)


def should_suppress(prompt: str) -> bool:
    stripped = prompt.lstrip()
    if stripped.startswith(ALLOWLIST_PREFIXES):
        return True
    low = prompt.lower()
    return any(p in low for p in ALLOWLIST_PHRASES)


def has_exec_keyword(prompt: str) -> bool:
    low = prompt.lower()
    return any(k.lower() in low for k in EXEC_KEYWORDS)


def main() -> int:
    if (Path.cwd() / ".copilot" / "dispatch-reminder.disabled").exists():
        return 0

    prompt = sys.stdin.read()
    if should_suppress(prompt):
        return 0
    if not has_exec_keyword(prompt):
        return 0

    sys.stdout.write(
        "[dispatch-reminder] Detected execution-class task. Before doing it inline, dispatch a sub-agent:\n"
        "  - literature / paper search -> Agent(subagent_type='copilot-literature')\n"
        "  - innovation / brainstorm -> Agent(subagent_type='copilot-ideation')\n"
        "  - experiment / training -> Agent(subagent_type='copilot-experiment')\n"
        "  - drafting / writing -> Agent(subagent_type='copilot-writer')\n"
        "  - polish / de-AI -> Agent(subagent_type='copilot-polisher')\n"
        "  - review / sanity -> Agent(subagent_type='copilot-reviewer')\n"
        "  - rebuttal -> Agent(subagent_type='copilot-rebuttal')\n"
        "  - full pipeline / routing -> Agent(subagent_type='research-copilot')\n"
        "Skip dispatch only if: simple question, status query, file-list, or user explicitly asked inline execution.\n"
    )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
