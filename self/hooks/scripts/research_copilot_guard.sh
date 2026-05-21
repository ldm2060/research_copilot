#!/usr/bin/env bash
# Research Copilot Guard wrapper (POSIX).
# Tries to run the Python guard; if Python is unavailable, emits an
# allow decision so the prompt-based fallback hook can take over.

set -e

script_dir="$(cd "$(dirname "$0")" && pwd)"

if command -v python >/dev/null 2>&1; then
  exec python "$script_dir/research_copilot_guard.py"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$script_dir/research_copilot_guard.py"
fi

# Drain stdin so the harness does not block on a closed pipe.
cat >/dev/null

printf '%s\n' '{"hookSpecificOutput":{"permissionDecision":"allow"},"systemMessage":"research-copilot-guard: Python unavailable; deferring to prompt-based fallback and skill HARD-GATE blocks."}'
exit 0
