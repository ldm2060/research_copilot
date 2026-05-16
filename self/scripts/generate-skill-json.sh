#!/usr/bin/env bash
# Generate skill.json metadata next to each SKILL.md.
#
# Claude Code 2.1.142 (released 2026-05-15) requires every plugin skill to
# ship a sibling skill.json. This wrapper delegates to the cross-platform
# Python implementation so the same command works on Linux, macOS, and
# Git Bash on Windows.
#
# Usage:
#   bash self/scripts/generate-skill-json.sh           # regenerate as needed
#   bash self/scripts/generate-skill-json.sh --check   # CI mode (non-zero on drift)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/generate-skill-json.py"

if [ ! -f "$PY_SCRIPT" ]; then
  echo "[error] missing $PY_SCRIPT" >&2
  exit 2
fi

# Prefer python3, fall back to python (Windows Git Bash often only has `python`).
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[error] neither python3 nor python is on PATH" >&2
  exit 2
fi

exec "$PY" "$PY_SCRIPT" "$@"
