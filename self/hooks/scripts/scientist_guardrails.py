from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    workspace = Path.cwd()
    packaged_runtime = workspace / ".github" / "skills" / "scientist-support" / "runtime"
    source_runtime = workspace / "self" / "skills" / "scientist-support" / "runtime"
    lines = [
        "[scientist-guardrails] AI Scientist workflow loaded.",
        "[scientist-guardrails] Upstream defaults assume Linux + CUDA and may not fully run on Windows hosts.",
        "[scientist-guardrails] AI Scientist executes LLM-written code; prefer a container or sandbox before running full experiments.",
    ]
    if packaged_runtime.exists():
        lines.append(f"[scientist-guardrails] Detected skill runtime: {packaged_runtime}")
    elif source_runtime.exists():
        lines.append(f"[scientist-guardrails] Detected skill runtime: {source_runtime}")
    else:
        lines.append("[scientist-guardrails] Scientist-support runtime was not found in the workspace.")
    lines.append("[scientist-guardrails] Recommended first action: run scientist runtime validation before ideation or experiment launch.")
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())