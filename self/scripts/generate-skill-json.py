#!/usr/bin/env python3
"""Generate skill.json metadata next to each SKILL.md.

Claude Code 2.1.142 (released 2026-05-15) requires every plugin skill to
ship a sibling `skill.json` next to its `SKILL.md`. Skills without one are
silently dropped from discovery.

This script walks `self/skills/<name>/SKILL.md`, parses the YAML
frontmatter, and writes `self/skills/<name>/skill.json` with the shape:

    {
      "name": "<name>",
      "description": "<description>",
      "entry": "SKILL.md"
    }

Idempotent: re-running emits `[skipped]` for unchanged skills.

Usage:
    python self/scripts/generate-skill-json.py [--root DIR] [--check]

`--check` exits non-zero if any skill.json is missing or stale, without
writing. Useful in CI / pre-commit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_FIELDS = ("name", "description")


def parse_frontmatter(text: str) -> dict[str, str]:
    """Hand-rolled YAML frontmatter parser. Only handles the subset we use:
    `key: value` and `key: "value"` with optional multi-line `>`-folded
    scalars. No external deps.
    """
    if not text.startswith("---"):
        raise ValueError("missing frontmatter opening fence")
    lines = text.splitlines()
    if lines[0].strip() != "---":
        raise ValueError("first line is not '---'")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("missing frontmatter closing fence")

    fields: dict[str, str] = {}
    i = 1
    while i < end:
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if ":" not in stripped:
            i += 1
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value == ">" or value == ">-" or value == "|":
            # folded / literal scalar — gather indented continuation lines
            parts: list[str] = []
            i += 1
            while i < end and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                parts.append(lines[i].strip())
                i += 1
            joined = " ".join(parts) if value == ">" else "\n".join(parts)
            fields[key] = joined.strip()
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
            # unescape \"
            value = value.replace('\\"', '"')
        fields[key] = value
        i += 1
    return fields


def build_skill_json(name: str, description: str) -> dict[str, str]:
    return {"name": name, "description": description, "entry": "SKILL.md"}


def serialize(obj: dict[str, str]) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def process_skill(skill_md: Path, *, check: bool, missing_only: bool = False) -> str:
    """Return 'ok' | 'updated' | 'skipped' | 'missing' (for --check) | 'stale'.

    Raises on parse error. With ``missing_only=True``, never touch an existing
    skill.json — only generate when absent.
    """
    target = skill_md.parent / "skill.json"
    if missing_only and target.exists():
        return "skipped"
    text = skill_md.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    for field in REQUIRED_FIELDS:
        if field not in frontmatter or not frontmatter[field]:
            raise ValueError(f"{skill_md}: missing required field '{field}'")
    payload = build_skill_json(frontmatter["name"], frontmatter["description"])
    new_text = serialize(payload)
    if target.exists():
        old_text = target.read_text(encoding="utf-8")
        if old_text == new_text:
            return "skipped"
        if check:
            return "stale"
        target.write_text(new_text, encoding="utf-8")
        return "updated"
    if check:
        return "missing"
    target.write_text(new_text, encoding="utf-8")
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Path to the skills/ directory (default: <script>/../skills).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any skill.json is missing or stale. Do not write.",
    )
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Generate skill.json only for skills that lack one; never overwrite. "
        "Use this when packaging third-party skills whose existing skill.json must be preserved.",
    )
    args = parser.parse_args()

    if args.root is None:
        args.root = Path(__file__).resolve().parent.parent / "skills"
    if not args.root.exists():
        print(f"[error] skills directory not found: {args.root}", file=sys.stderr)
        return 2

    skill_mds = sorted(args.root.glob("*/SKILL.md"))
    if not skill_mds:
        print(f"[error] no SKILL.md files under {args.root}", file=sys.stderr)
        return 2

    counts = {"ok": 0, "updated": 0, "skipped": 0, "missing": 0, "stale": 0}
    for skill_md in skill_mds:
        try:
            status = process_skill(skill_md, check=args.check, missing_only=args.missing_only)
        except ValueError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 1
        counts[status] = counts.get(status, 0) + 1
        print(f"[{status}] {skill_md.parent.name}")

    if args.check and (counts["missing"] or counts["stale"]):
        print(
            f"[fail] {counts['missing']} missing, {counts['stale']} stale "
            "skill.json file(s). Run without --check to regenerate.",
            file=sys.stderr,
        )
        return 1
    summary = ", ".join(f"{k}={v}" for k, v in counts.items() if v)
    print(f"[done] {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
