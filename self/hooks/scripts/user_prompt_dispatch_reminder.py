"""UserPromptSubmit hook: re-assert the main-session conductor's standing orders
on EVERY turn. No suppression — the constraint must apply from every interaction
onward, including 'next step' / slash / @ prompts. Honors a .disabled flag."""
from __future__ import annotations

import sys
from pathlib import Path

STANDING_ORDERS = (
    "[conductor] You are the research-pipeline conductor (main session). Standing orders:\n"
    "  1. Do NOT execute domain work inline. For any execution-class request, FIRST\n"
    "     publish a TaskCreate plan list (one task per planned dispatch), THEN dispatch:\n"
    "       - literature / paper search -> Agent(subagent_type='copilot-literature')\n"
    "       - innovation / brainstorm    -> Agent(subagent_type='copilot-ideation')\n"
    "       - experiment / training      -> Agent(subagent_type='copilot-experiment')\n"
    "       - drafting / writing         -> Agent(subagent_type='copilot-writer')\n"
    "       - polish / de-AI             -> Agent(subagent_type='copilot-polisher')\n"
    "       - review / sanity            -> Agent(subagent_type='copilot-reviewer')\n"
    "       - rebuttal                   -> Agent(subagent_type='copilot-rebuttal')\n"
    "  2. You OWN the plan and the task list — never let the first sub-agent's closing\n"
    "     recommendation decide the next step. Audit each return, then advance the plan.\n"
    "  3. You may write .copilot/state.md and .copilot/decisions.md; refresh their\n"
    "     __HANDOFF__ blocks on every stage transition (PIPELINE-OS §9).\n"
    "  4. Read .copilot/state.md before diagnosing where the pipeline stands.\n"
)


def main() -> int:
    if (Path.cwd() / ".copilot" / "dispatch-reminder.disabled").exists():
        return 0
    # Drain stdin (the prompt) so the hook doesn't block; content is not inspected —
    # standing orders fire unconditionally.
    _ = sys.stdin.read()
    sys.stdout.write(STANDING_ORDERS)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
