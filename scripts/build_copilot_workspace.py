from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
SKIP_NAMES = {".git", "__pycache__", ".DS_Store"}
VALID_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
AGENT_TOOL_MAP = {
    "conductor": ["read", "search", "edit", "execute", "agent", "todo"],
    "experiment-driver": ["read", "search", "edit", "execute", "todo"],
    "literature-scout": ["read", "search", "web", "todo"],
    "paper-writer": ["read", "search", "edit", "todo"],
    "reviewer": ["read", "search", "todo"],
}
AGENT_DESCRIPTION_MAP = {
    "conductor": "研究与论文流程总控 agent。Use when: coordinating multi-step research or paper workflows, choosing the next step, or routing work to specialist agents.",
    "experiment-driver": "实验执行与结果核对 agent。Use when: planning or running experiments, tracing numbers to evidence, or checking whether evaluation coverage is sufficient.",
    "literature-scout": "文献与引用核验 agent。Use when: searching papers, building related work, verifying citations, or mapping prior art around a research claim.",
    "paper-writer": "论文写作 agent。Use when: drafting or revising sections, polishing LaTeX prose, writing captions, or turning results into paper-ready text.",
    "reviewer": "论文审稿式质量检查 agent。Use when: critically reviewing a paper, stress-testing claims, finding narrative or citation risks, or preparing for submission.",
}


@dataclass
class CopiedItem:
    kind: str
    name: str
    source: str
    target: str
    operation: str
    transformed: bool = False
    note: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a GitHub Copilot workspace bundle from skill.txt and agent.txt.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root containing manifests.")
    parser.add_argument("--skills-manifest", default="skill.txt", help="Path to the skill manifest.")
    parser.add_argument("--agents-manifest", default="agent.txt", help="Path to the agent manifest.")
    parser.add_argument(
        "--output",
        default="dist/copilot-workspace",
        help="Output directory for the generated workspace bundle.",
    )
    return parser.parse_args()


def parse_manifest(manifest_path: Path) -> list[tuple[int, str, str]]:
    entries: list[tuple[int, str, str]] = []
    for line_no, raw_line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or parts[0] not in {"add", "del"}:
            raise ValueError(f"{manifest_path}:{line_no}: unsupported manifest entry: {raw_line}")
        entries.append((line_no, parts[0], parts[1].strip()))
    return entries


def repo_path(repo_root: Path, raw_path: str) -> Path:
    normalized = raw_path.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part]
    return repo_root.joinpath(*parts)


def reset_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_file() or path.is_symlink():
        path.unlink()
        return
    shutil.rmtree(path)


def copy_tree(src: Path, dest: Path) -> None:
    reset_path(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(*SKIP_NAMES),
    )


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def read_frontmatter(text: str) -> tuple[str | None, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    return match.group(1), text[match.end():].lstrip("\n")


def read_frontmatter_field(path: Path, field: str) -> str | None:
    frontmatter, _ = read_frontmatter(path.read_text(encoding="utf-8"))
    if frontmatter is None:
        return None
    wanted = f"{field}:"
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.lower().startswith(wanted):
            return strip_quotes(stripped.split(":", 1)[1])
    return None


def is_skill_dir(path: Path) -> bool:
    return path.is_dir() and (path / "SKILL.md").is_file()


def is_skill_container(path: Path) -> bool:
    if not path.is_dir() or is_skill_dir(path):
        return False
    return any(is_skill_dir(child) for child in path.iterdir() if child.is_dir())


def is_agent_file(path: Path) -> bool:
    return path.is_file() and (
        path.name.endswith(".agent.md") or path.suffix.lower() == ".md"
    )


def list_add_sources(repo_root: Path, kind: str, raw_path: str) -> list[Path]:
    if raw_path.endswith("\\*") or raw_path.endswith("/*"):
        base_dir = repo_path(repo_root, raw_path[:-2])
        if not base_dir.is_dir():
            raise FileNotFoundError(f"Source directory not found: {base_dir}")
        children = sorted(
            child for child in base_dir.iterdir() if child.name not in SKIP_NAMES and not child.name.startswith(".")
        )
        if kind == "skill":
            return [child for child in children if child.is_dir()]
        return [child for child in children if child.is_dir() or is_agent_file(child)]
    return [repo_path(repo_root, raw_path)]


def derive_skill_name(source_dir: Path) -> str:
    frontmatter_name = read_frontmatter_field(source_dir / "SKILL.md", "name")
    if frontmatter_name and VALID_SKILL_NAME_RE.fullmatch(frontmatter_name):
        return frontmatter_name
    if VALID_SKILL_NAME_RE.fullmatch(source_dir.name):
        return source_dir.name

    candidate = slugify_skill_name(frontmatter_name or source_dir.name)
    if candidate:
        return candidate
    raise ValueError(f"Unable to derive a valid skill name from {source_dir}")


def slugify_skill_name(value: str) -> str:
    slug = value.strip().lower().replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:64]


def rewrite_skill_name(skill_md_path: Path, skill_name: str) -> None:
    original_text = skill_md_path.read_text(encoding="utf-8")
    frontmatter, body = read_frontmatter(original_text)
    if frontmatter is None:
        return

    updated_lines: list[str] = []
    replaced = False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("name:"):
            updated_lines.append(f"name: {skill_name}")
            replaced = True
        else:
            updated_lines.append(line)
    if not replaced:
        updated_lines.insert(0, f"name: {skill_name}")

    updated_text = "---\n" + "\n".join(updated_lines) + "\n---\n\n" + body
    skill_md_path.write_text(updated_text, encoding="utf-8")


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return None


def first_paragraph(text: str) -> str | None:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        if stripped.startswith("#"):
            continue
        lines.append(stripped)
    if not lines:
        return None
    return " ".join(lines)


def normalize_agent_body(text: str) -> str:
    return (
        text.replace(".claude/skills/", ".github/skills/")
        .replace(".agents/skills/", ".github/skills/")
    )


def fallback_agent_description(source_name: str, body: str) -> str:
    mapped = AGENT_DESCRIPTION_MAP.get(source_name)
    if mapped:
        return mapped
    heading = first_heading(body)
    paragraph = first_paragraph(body)
    if heading and paragraph:
        return f"{heading}。Use when: {paragraph[:180]}"
    if heading:
        return f"{heading}。Use when this specialized workflow matches the current task in this workspace."
    return f"Imported agent {source_name}. Use when this specialized workflow matches the current task in this workspace."


def build_agent_frontmatter(source_name: str, body: str) -> str:
    description = fallback_agent_description(source_name, body).replace('"', "'")
    tools = AGENT_TOOL_MAP.get(source_name, ["read", "search"])
    lines = [
        "---",
        f'name: {source_name}',
        f'description: "{description}"',
        f"tools: [{', '.join(tools)}]",
        "---",
        "",
    ]
    return "\n".join(lines)


def normalize_agent_markdown(source_file: Path) -> tuple[str, bool]:
    raw_text = normalize_agent_body(source_file.read_text(encoding="utf-8"))
    if source_file.name.endswith(".agent.md"):
        return raw_text, False

    source_name = source_file.stem
    frontmatter, body = read_frontmatter(raw_text)
    if frontmatter is not None:
        frontmatter_lines = frontmatter.splitlines()
        if not any(line.strip().startswith("description:") for line in frontmatter_lines):
            frontmatter_lines.append(
                f'description: "{fallback_agent_description(source_name, body).replace(chr(34), chr(39))}"'
            )
        updated = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body
        return updated, True

    updated = build_agent_frontmatter(source_name, raw_text) + raw_text.lstrip("\n")
    return updated, True


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def add_skill_source(source: Path, target_base: Path, report: list[CopiedItem], warnings: list[str]) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Skill source not found: {source}")

    if source.is_dir() and source.name == "skills":
        for child in sorted(source.iterdir()):
            if child.name in SKIP_NAMES or child.name.startswith("."):
                continue
            add_skill_source(child, target_base, report, warnings)
        return

    if is_skill_dir(source):
        original_frontmatter_name = read_frontmatter_field(source / "SKILL.md", "name")
        skill_name = derive_skill_name(source)
        destination = target_base / skill_name
        copy_tree(source, destination)
        rewrite_skill_name(destination / "SKILL.md", skill_name)
        report.append(
            CopiedItem(
                kind="skill",
                name=skill_name,
                source=str(source),
                target=str(destination),
                operation="add",
                transformed=skill_name != source.name or skill_name != (original_frontmatter_name or source.name),
                note="normalized-skill-name"
                if skill_name != source.name or skill_name != (original_frontmatter_name or source.name)
                else None,
            )
        )
        return

    if is_skill_container(source):
        destination = target_base / source.name
        copy_tree(source, destination)
        report.append(
            CopiedItem(
                kind="skill-container",
                name=source.name,
                source=str(source),
                target=str(destination),
                operation="add",
                note="container-copied-verbatim",
            )
        )
        return

    warnings.append(f"Skipped non-skill directory: {source}")


def add_agent_source(source: Path, target_base: Path, report: list[CopiedItem], warnings: list[str]) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Agent source not found: {source}")

    if source.is_dir() and source.name == "agents":
        for child in sorted(source.iterdir()):
            if child.name in SKIP_NAMES or child.name.startswith("."):
                continue
            add_agent_source(child, target_base, report, warnings)
        return

    if is_agent_file(source):
        if not source.read_text(encoding="utf-8").strip():
            warnings.append(f"Skipped empty agent file: {source}")
            return
        output_name = source.name if source.name.endswith(".agent.md") else f"{source.stem}.agent.md"
        destination = target_base / output_name
        normalized_text, transformed = normalize_agent_markdown(source)
        write_text(destination, normalized_text)
        report.append(
            CopiedItem(
                kind="agent",
                name=output_name,
                source=str(source),
                target=str(destination),
                operation="add",
                transformed=transformed or output_name != source.name,
                note="normalized-to-agent-file" if transformed or output_name != source.name else None,
            )
        )
        return

    warnings.append(f"Skipped non-agent entry: {source}")


def apply_manifest(
    repo_root: Path,
    manifest_path: Path,
    kind: str,
    target_base: Path,
    report: list[CopiedItem],
    warnings: list[str],
) -> None:
    for line_no, action, raw_path in parse_manifest(manifest_path):
        if action == "del":
            destination = target_base / raw_path.replace("\\", "/").strip("/")
            if destination.exists() or destination.is_symlink():
                reset_path(destination)
                report.append(
                    CopiedItem(
                        kind=kind,
                        name=destination.name,
                        source=str(manifest_path),
                        target=str(destination),
                        operation="del",
                    )
                )
            else:
                warnings.append(f"{manifest_path}:{line_no}: delete skipped because target does not exist: {destination}")
            continue

        sources = list_add_sources(repo_root, kind, raw_path)
        for source in sources:
            if kind == "skill":
                add_skill_source(source, target_base, report, warnings)
            else:
                add_agent_source(source, target_base, report, warnings)


def write_summary(
    output_root: Path,
    skills_target: Path,
    agents_target: Path,
    report: list[CopiedItem],
    warnings: list[str],
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    manifest_path = output_root / "BUILD_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": timestamp,
                "items": [asdict(item) for item in report],
                "warnings": warnings,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    skill_names = sorted(child.name for child in skills_target.iterdir() if child.is_dir())
    agent_names = sorted(child.name for child in agents_target.iterdir() if child.is_file())
    lines = [
        "# Copilot Workspace Bundle",
        "",
        f"Generated at: {timestamp}",
        "",
        "Extract this artifact into a workspace root. The resulting customizations live under `.github/skills/` and `.github/agents/`.",
        "",
        f"Skills: {len(skill_names)}",
    ]
    lines.extend(f"- {name}" for name in skill_names)
    lines.extend(["", f"Agents: {len(agent_names)}"])
    lines.extend(f"- {name}" for name in agent_names)
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in warnings)
    lines.append("")
    (output_root / "README.md").write_text("\n".join(lines), encoding="utf-8")


def create_zip(output_root: Path) -> Path:
    archive_base = output_root.parent / output_root.name
    zip_path = archive_base.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(archive_base), "zip", root_dir=output_root.parent, base_dir=output_root.name)
    return zip_path


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_root = (repo_root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    skills_manifest = (repo_root / args.skills_manifest).resolve()
    agents_manifest = (repo_root / args.agents_manifest).resolve()

    reset_path(output_root)
    skills_target = output_root / ".github" / "skills"
    agents_target = output_root / ".github" / "agents"
    skills_target.mkdir(parents=True, exist_ok=True)
    agents_target.mkdir(parents=True, exist_ok=True)

    report: list[CopiedItem] = []
    warnings: list[str] = []

    apply_manifest(repo_root, skills_manifest, "skill", skills_target, report, warnings)
    apply_manifest(repo_root, agents_manifest, "agent", agents_target, report, warnings)
    write_summary(output_root, skills_target, agents_target, report, warnings)
    zip_path = create_zip(output_root)

    print(f"Workspace bundle written to {output_root}")
    print(f"Zip archive written to {zip_path}")
    if warnings:
        print(f"Completed with {len(warnings)} warning(s). See {output_root / 'BUILD_MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())