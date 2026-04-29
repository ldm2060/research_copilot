from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
SKIP_NAMES = {".git", "__pycache__", ".DS_Store"}
VALID_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SCIENTIST_SUPPORT_RUNTIME_EXCLUDES = [
    "runtime/ai_scientist",
    "runtime/launch_scientist_bfts.py",
    "runtime/bfts_config.yaml",
    "runtime/requirements.txt",
]
AGENT_TOOL_MAP = {
    "conductor": ["read", "search", "edit", "execute", "agent", "todo", "arxiv-search/*", "dblp-bib/*", "google-scholar/*"],
    "experiment-driver": ["read", "search", "edit", "execute", "todo", "google-scholar/*"],
    "literature-scout": ["read", "search", "web", "todo", "arxiv-search/*", "dblp-bib/*", "google-scholar/*"],
    "paper-writer": ["read", "search", "edit", "todo", "arxiv-search/*", "dblp-bib/*", "google-scholar/*"],
    "reviewer": ["read", "search", "todo", "arxiv-search/*", "dblp-bib/*", "google-scholar/*"],
}
AGENT_DESCRIPTION_MAP = {
    "conductor": "研究与论文流程总控 agent。Use when: coordinating multi-step research or paper workflows, choosing the next step, or routing work to specialist agents.",
    "experiment-driver": "实验执行与结果核对 agent。Use when: planning or running experiments, tracing numbers to evidence, or checking whether evaluation coverage is sufficient.",
    "literature-scout": "文献与引用核验 agent。Use when: searching papers, building related work, verifying citations, or mapping prior art around a research claim.",
    "paper-writer": "论文写作 agent。Use when: drafting or revising sections, polishing LaTeX prose, writing captions, or turning results into paper-ready text.",
    "reviewer": "论文审稿式质量检查 agent。Use when: critically reviewing a paper, stress-testing claims, finding narrative or citation risks, or preparing for submission.",
}
CITATION_POLICY_AGENT_NAMES = {"conductor", "literature-scout", "paper-writer", "reviewer"}
CITATION_POLICY_HEADER = "## 引用修改约束"
CITATION_POLICY_BLOCK = """## 引用修改约束

- 当任务涉及新增、替换、修正或核对 BibTeX / references.bib / 引文元数据时，只能使用 `dblp-bib` MCP 工具作为外部引用来源。
- 不得根据记忆、普通网页搜索结果、其他 MCP、或现有不可信草稿手工编造 BibTeX 条目。
- 如果 `dblp-bib` 没有返回唯一且可信的记录，必须停止修改该条引用，并向用户报告缺口或保留占位符。
- 当需要查找、检索、了解一篇论文时，必须优先使用 `arxiv-search` MCP；只有在无结果时才回退到普通 web 搜索。
"""

COPILOT_INSTRUCTIONS = """\
- **对话风格**: 每次完成任务后，绝对不要停止对话。必须调用vscode ask user question工具提供几个选项供用户选择下一步操作，最后一个选项固定为"让我自由输入"。即使用户选了"自由输入"，也要继续等待用户输入，不能只回复一句话就停下。总之任何情况下都要保持对话进行，始终以调用vscode ask user question工具结尾。

- **额度保护**: 当前为按次计费模式。严禁任何浪费请求次数的操作（包括调用子 Agent、后台自主运行、无限制的自动报错重试等）。在执行任何可能产生多次 API 调用的复合任务前，必须先暂停并调用vscode ask user question工具，向用户说明预估步骤，征得明确同意后才可继续执行。
- **网络搜索失败处理**: WebSearch/WebFetch/API调用如果第一次失败（无结果、限流、超时），**立即停下调用vscode ask user question工具问用户**，绝对不要自行重试或换方式连续尝试。每多一次无效的网络调用都是浪费额度。
- **委托外部执行**: 当任务涉及大量网络搜索、文献检索等不确定性高的操作时，应先写出明确的规划（搜索关键词、期望结果格式、目的），交给用户委托不按次计费的渠道执行，而非自己消耗额度尝试。
"""

COPILOT_TO_CLAUDE_TOOLS: dict[str, list[str]] = {
    "read": ["Read"],
    "search": ["Glob", "Grep"],
    "edit": ["Edit", "Write"],
    "execute": ["Bash"],
    "web": ["WebSearch", "WebFetch"],
    "todo": ["TodoWrite"],
    "agent": ["Agent"],
}

CLAUDE_CODE_INSTRUCTIONS = """\
- **对话风格**: 每次完成任务后，绝对不要停止对话。必须提供几个选项供用户选择下一步操作，最后一个选项固定为"让我自由输入"。即使用户选了"自由输入"，也要继续等待用户输入，不能只回复一句话就停下。总之任何情况下都要保持对话进行，始终以提供选项结尾。

- **额度保护**: 当前为按次计费模式。严禁任何浪费请求次数的操作（包括调用子 Agent、后台自主运行、无限制的自动报错重试等）。在执行任何可能产生多次 API 调用的复合任务前，必须先暂停并向用户说明预估步骤，征得明确同意后才可继续执行。

- **网络搜索失败处理**: WebSearch/WebFetch/API调用如果第一次失败（无结果、限流、超时），**立即停下问用户**，绝对不要自行重试或换方式连续尝试。每多一次无效的网络调用都是浪费额度。

- **委托外部执行**: 当任务涉及大量网络搜索、文献检索等不确定性高的操作时，应先写出明确的规划（搜索关键词、期望结果格式、目的），交给用户委托不按次计费的渠道执行，而非自己消耗额度尝试。
"""


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
        description="Build a GitHub Copilot workspace bundle from skill.txt, agent.txt, and hook.txt.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root containing manifests.")
    parser.add_argument("--skills-manifest", default="skill.txt", help="Path to the skill manifest.")
    parser.add_argument("--agents-manifest", default="agent.txt", help="Path to the agent manifest.")
    parser.add_argument("--hooks-manifest", default="hook.txt", help="Path to the hook manifest.")
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


def copy_file(src: Path, dest: Path) -> None:
    reset_path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def prune_scientist_support_runtime(skill_dir: Path, warnings: list[str]) -> None:
    if skill_dir.name != "scientist-support":
        return
    for relative_path in SCIENTIST_SUPPORT_RUNTIME_EXCLUDES:
        target = skill_dir / relative_path.replace("/", os.sep)
        if target.exists() or target.is_symlink():
            reset_path(target)


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
        if kind == "agent":
            return [child for child in children if child.is_dir() or is_agent_file(child)]
        return [child for child in children if child.is_dir() or child.is_file() or child.is_symlink()]
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


def apply_citation_policy(source_name: str, body: str) -> str:
    if source_name not in CITATION_POLICY_AGENT_NAMES or CITATION_POLICY_HEADER in body:
        return body
    return body.rstrip() + "\n\n" + CITATION_POLICY_BLOCK.strip() + "\n"


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
    raw_text = apply_citation_policy(
        source_file.stem,
        normalize_agent_body(source_file.read_text(encoding="utf-8")),
    )
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


def package_mcp_configuration(
    repo_root: Path,
    output_root: Path,
    report: list[CopiedItem],
    warnings: list[str],
) -> list[str]:
    source_root = repo_root / "self" / "mcp"
    if not source_root.is_dir():
        return []

    vscode_target = output_root / ".vscode"
    vscode_target.mkdir(parents=True, exist_ok=True)
    server_names: list[str] = []

    mcp_config_source = source_root / "mcp.json"
    if mcp_config_source.is_file():
        mcp_text = mcp_config_source.read_text(encoding="utf-8")
        try:
            server_names = sorted(json.loads(mcp_text).get("servers", {}).keys())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid MCP config JSON at {mcp_config_source}: {exc}") from exc
        destination = vscode_target / "mcp.json"
        write_text(destination, mcp_text)
        report.append(
            CopiedItem(
                kind="mcp-config",
                name="mcp.json",
                source=str(mcp_config_source),
                target=str(destination),
                operation="add",
            )
        )
    else:
        warnings.append(f"Missing self/mcp/mcp.json; MCP servers will not be configured automatically.")

    servers_source = source_root / "servers"
    if servers_source.is_dir():
        servers_target = vscode_target / "mcp-servers"
        copy_tree(servers_source, servers_target)
        for child in sorted(servers_source.iterdir()):
            if child.name in SKIP_NAMES or child.name.startswith("."):
                continue
            report.append(
                CopiedItem(
                    kind="mcp-server",
                    name=child.name,
                    source=str(child),
                    target=str(servers_target / child.name),
                    operation="add",
                )
            )
    elif server_names:
        warnings.append("MCP config exists but self/mcp/servers is missing.")

    return server_names


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

    if source.is_dir():
        destination = target_base / source.name
        copy_tree(source, destination)
        prune_scientist_support_runtime(destination, warnings)
        report.append(
            CopiedItem(
                kind="skill-directory",
                name=source.name,
                source=str(source),
                target=str(destination),
                operation="add",
                note="directory-copied-with-runtime-prune" if source.name == "scientist-support" else "directory-copied-verbatim",
            )
        )
        return

    warnings.append(f"Skipped non-directory skill entry: {source}")


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


def add_hook_source(source: Path, target_base: Path, report: list[CopiedItem], warnings: list[str]) -> None:
    if not source.exists() and not source.is_symlink():
        raise FileNotFoundError(f"Hook source not found: {source}")

    if source.is_dir() and source.name == "hooks":
        for child in sorted(source.iterdir()):
            if child.name in SKIP_NAMES or child.name.startswith("."):
                continue
            add_hook_source(child, target_base, report, warnings)
        return

    destination = target_base / source.name
    if source.is_dir():
        copy_tree(source, destination)
        report.append(
            CopiedItem(
                kind="hook-directory",
                name=source.name,
                source=str(source),
                target=str(destination),
                operation="add",
                note="directory-copied-verbatim",
            )
        )
        return

    if source.is_file() or source.is_symlink():
        copy_file(source, destination)
        report.append(
            CopiedItem(
                kind="hook",
                name=source.name,
                source=str(source),
                target=str(destination),
                operation="add",
            )
        )
        return

    warnings.append(f"Skipped non-hook entry: {source}")


def apply_manifest(
    repo_root: Path,
    manifest_path: Path,
    kind: str,
    target_base: Path,
    report: list[CopiedItem],
    warnings: list[str],
) -> None:
    if not manifest_path.is_file():
        if kind == "hook":
            return
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

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
            elif kind == "agent":
                add_agent_source(source, target_base, report, warnings)
            else:
                add_hook_source(source, target_base, report, warnings)


def write_copilot_instructions(
    output_root: Path,
    report: list[CopiedItem],
) -> None:
    github_dir = output_root / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    destination = github_dir / "copilot-instructions.md"
    write_text(destination, COPILOT_INSTRUCTIONS)
    report.append(
        CopiedItem(
            kind="instruction",
            name="copilot-instructions.md",
            source="(generated)",
            target=str(destination),
            operation="add",
        )
    )


def write_bundle_readme(
    output_root: Path,
    bundle_type: str,
    skills_target: Path,
    agents_target: Path,
    hooks_target: Path | None,
    mcp_servers: list[str],
    report: list[CopiedItem],
    warnings: list[str],
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    manifest_data: dict = {
        "generated_at": timestamp,
        "bundle_type": bundle_type,
        "items": [asdict(item) for item in report],
        "warnings": warnings,
    }
    (output_root / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8",
    )

    skill_names = sorted(
        child.name
        for child in skills_target.iterdir()
        if child.is_dir() and (child / "SKILL.md").is_file()
    )
    support_names = sorted(
        child.name
        for child in skills_target.iterdir()
        if child.is_dir() and not (child / "SKILL.md").is_file()
    )
    agent_names = sorted(child.name for child in agents_target.iterdir() if child.is_file())

    lines: list[str] = []
    if bundle_type == "copilot":
        lines += [
            "# Copilot Workspace Bundle",
            "", f"Generated at: {timestamp}", "",
            "Extract this artifact into a workspace root. The resulting customizations live under `.github/skills/`, `.github/agents/`, `.github/hooks/`, and `.vscode/` for MCP configuration.",
        ]
    elif bundle_type == "claude":
        lines += [
            "# Claude Code Workspace Bundle",
            "", f"Generated at: {timestamp}", "",
            "Extract this artifact into a workspace root. The resulting customizations live under `.claude/skills/`, `.claude/agents/`, `.claude/settings.json`, `.mcp.json`, and `CLAUDE.md`.",
        ]
    else:
        lines += [
            "# Copilot + Claude Code Workspace Bundle",
            "", f"Generated at: {timestamp}", "",
            "Extract this artifact into a workspace root. The resulting customizations live under `.github/skills/`, `.github/agents/`, `.github/hooks/`, and `.vscode/` for MCP configuration.",
            "",
            "## Claude Code Compatibility", "",
            "This bundle also includes Claude Code compatible configuration:",
            "- `.claude/skills/` — skills (copied from `.github/skills/`)",
            "- `.claude/agents/` — agents (transformed for Claude Code tool names)",
            "- `.claude/settings.json` — hooks and permissions",
            "- `.mcp.json` — MCP server configuration (Claude Code format)",
            "- `CLAUDE.md` — behavioral instructions",
        ]

    lines += ["", f"Skills: {len(skill_names)}"]
    lines.extend(f"- {name}" for name in skill_names)
    if support_names:
        lines += ["", f"Support directories: {len(support_names)}"]
        lines.extend(f"- {name}" for name in support_names)
    lines += ["", f"Agents: {len(agent_names)}"]
    lines.extend(f"- {name}" for name in agent_names)
    if hooks_target and hooks_target.is_dir():
        hook_names = sorted(child.name for child in hooks_target.iterdir())
        lines += ["", f"Hooks: {len(hook_names)}"]
        lines.extend(f"- {name}" for name in hook_names)
    if mcp_servers:
        lines += ["", f"MCP servers: {len(mcp_servers)}"]
        lines.extend(f"- {name}" for name in mcp_servers)
    if warnings:
        lines += ["", "Warnings:"]
        lines.extend(f"- {w}" for w in warnings)
    lines.append("")
    (output_root / "README.md").write_text("\n".join(lines), encoding="utf-8")


def create_zip(output_root: Path) -> Path:
    archive_base = output_root.parent / output_root.name
    zip_path = archive_base.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(
            output_root, followlinks=True
        ):
            rel_dir = os.path.relpath(dirpath, output_root.parent)
            zf.write(dirpath, rel_dir)
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                zf.write(fp, os.path.join(rel_dir, fn))
    return zip_path


# --- Claude Code compatibility helpers ---

def symlink_or_copy(src: Path, dest: Path) -> None:
    """Create a relative symlink from dest to src, falling back to copy.

    Uses os.path.relpath so the symlink survives relocation of the bundle.
    """
    reset_path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        rel_src = os.path.relpath(str(src.resolve()), str(dest.parent.resolve()))
        os.symlink(rel_src, str(dest), target_is_directory=src.is_dir())
    except OSError:
        if src.is_dir():
            copy_tree(src, dest)
        else:
            copy_file(src, dest)


def transform_copilot_tools_to_claude(copilot_tools: list[str]) -> list[str]:
    """Convert Copilot tool names to Claude Code tool names."""
    claude_tools: list[str] = []
    for tool in copilot_tools:
        tool = tool.strip()
        if tool in COPILOT_TO_CLAUDE_TOOLS:
            claude_tools.extend(COPILOT_TO_CLAUDE_TOOLS[tool])
        elif "/*" in tool:
            server_name = tool.replace("/*", "")
            claude_tools.append(f"mcp__{server_name}")
        else:
            claude_tools.append(tool)
    seen: set[str] = set()
    result: list[str] = []
    for t in claude_tools:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def normalize_agent_for_claude_code(source_file: Path) -> tuple[str, bool]:
    """Transform a Copilot agent file for Claude Code compatibility."""
    raw_text = source_file.read_text(encoding="utf-8")
    body = raw_text.replace(".github/skills/", ".claude/skills/")
    frontmatter, content = read_frontmatter(body)
    transformed = False
    if frontmatter is not None:
        updated_lines: list[str] = []
        for line in frontmatter.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("tools:"):
                tools_str = stripped.split(":", 1)[1].strip()
                if tools_str.startswith("[") and tools_str.endswith("]"):
                    inner = tools_str[1:-1]
                    copilot_tools = [t.strip().strip("'\"") for t in inner.split(",")]
                    claude_tools = transform_copilot_tools_to_claude(copilot_tools)
                    updated_lines.append(f"tools: {', '.join(claude_tools)}")
                    transformed = True
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        body = "---\n" + "\n".join(updated_lines) + "\n---\n\n" + content
    return body, transformed


def generate_claude_mcp_config(copilot_mcp_path: Path) -> dict:
    """Generate Claude Code .mcp.json content from Copilot mcp.json."""
    copilot_config = json.loads(copilot_mcp_path.read_text(encoding="utf-8"))
    claude_servers: dict[str, dict] = {}
    for name, server_config in copilot_config.get("servers", {}).items():
        claude_server: dict[str, object] = {}
        server_type = server_config.get("type", "stdio")
        if server_type in ("http", "sse"):
            claude_server["type"] = server_type
            if "url" in server_config:
                claude_server["url"] = server_config["url"]
            if "headers" in server_config:
                claude_server["headers"] = server_config["headers"]
        else:
            if "command" in server_config:
                claude_server["command"] = server_config["command"]
            if "args" in server_config:
                claude_server["args"] = [
                    arg.replace("${workspaceFolder}", ".")
                    for arg in server_config["args"]
                ]
        if "env" in server_config:
            claude_server["env"] = server_config["env"]
        claude_servers[name] = claude_server
    return {"mcpServers": claude_servers}


def merge_hooks_to_claude_settings(hooks_dir: Path) -> dict:
    """Read hook files from Copilot hooks directory and merge into Claude Code settings.json format."""
    merged_hooks: dict[str, list] = {}
    if not hooks_dir.is_dir():
        return {"hooks": merged_hooks}
    for hook_file in sorted(hooks_dir.iterdir()):
        if hook_file.name in SKIP_NAMES or hook_file.name.startswith("."):
            continue
        if not hook_file.is_file() or not hook_file.name.endswith(".json"):
            continue
        try:
            data = json.loads(hook_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if "version" in data:
            continue
        hooks_data = data.get("hooks", {})
        if not isinstance(hooks_data, dict):
            continue
        for event, matchers in hooks_data.items():
            if event and event[0].islower():
                event = event[0].upper() + event[1:]
            if event not in merged_hooks:
                merged_hooks[event] = []
            if isinstance(matchers, list):
                merged_hooks[event].extend(matchers)
    for event in merged_hooks:
        for group in merged_hooks[event]:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                if "${CLAUDE_PLUGIN_ROOT}" in cmd:
                    hook["command"] = cmd.replace("${CLAUDE_PLUGIN_ROOT}", ".github")
    return {"hooks": merged_hooks}


def package_claude_code_workspace(
    output_root: Path,
    copilot_skills_dir: Path,
    copilot_agents_dir: Path,
    copilot_hooks_dir: Path,
    copilot_mcp_config: Path,
    report: list[CopiedItem],
    warnings: list[str],
) -> None:
    """Generate Claude Code compatible configuration alongside the Copilot bundle."""
    claude_dir = output_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # 1. Skills: relative symlink from .claude/skills/ to .github/skills/
    claude_skills = claude_dir / "skills"
    if copilot_skills_dir.is_dir():
        for skill_dir in sorted(copilot_skills_dir.iterdir()):
            if skill_dir.name in SKIP_NAMES or skill_dir.name.startswith("."):
                continue
            dest = claude_skills / skill_dir.name
            symlink_or_copy(skill_dir, dest)
            report.append(CopiedItem(
                kind="claude-skill",
                name=skill_dir.name,
                source=str(skill_dir),
                target=str(dest),
                operation="symlink",
            ))

    # 2. Agents: transform and write to .claude/agents/
    claude_agents = claude_dir / "agents"
    if copilot_agents_dir.is_dir():
        claude_agents.mkdir(parents=True, exist_ok=True)
        for agent_file in sorted(copilot_agents_dir.iterdir()):
            if agent_file.name in SKIP_NAMES or agent_file.name.startswith("."):
                continue
            if not agent_file.is_file():
                continue
            transformed_text, transformed = normalize_agent_for_claude_code(agent_file)
            output_name = agent_file.name
            if output_name.endswith(".agent.md"):
                output_name = output_name[: -len(".agent.md")] + ".md"
            dest = claude_agents / output_name
            write_text(dest, transformed_text)
            report.append(CopiedItem(
                kind="claude-agent",
                name=output_name,
                source=str(agent_file),
                target=str(dest),
                operation="transform",
                transformed=transformed or output_name != agent_file.name,
            ))

    # 3. Hooks: merge into .claude/settings.json
    settings = merge_hooks_to_claude_settings(copilot_hooks_dir)
    if copilot_mcp_config.is_file():
        copilot_mcp = json.loads(copilot_mcp_config.read_text(encoding="utf-8"))
        mcp_permissions = [f"mcp__{name}" for name in copilot_mcp.get("servers", {}).keys()]
        if mcp_permissions:
            settings["permissions"] = {"allow": mcp_permissions}
    settings_path = claude_dir / "settings.json"
    write_text(settings_path, json.dumps(settings, indent=2, ensure_ascii=False))
    report.append(CopiedItem(
        kind="claude-settings",
        name="settings.json",
        source=str(copilot_hooks_dir),
        target=str(settings_path),
        operation="merge",
    ))

    # 4. MCP: generate .mcp.json
    if copilot_mcp_config.is_file():
        claude_mcp = generate_claude_mcp_config(copilot_mcp_config)
        mcp_path = output_root / ".mcp.json"
        write_text(mcp_path, json.dumps(claude_mcp, indent=2, ensure_ascii=False))
        report.append(CopiedItem(
            kind="claude-mcp",
            name=".mcp.json",
            source=str(copilot_mcp_config),
            target=str(mcp_path),
            operation="transform",
        ))

    # 5. Instructions: generate CLAUDE.md
    claude_md_path = output_root / "CLAUDE.md"
    write_text(claude_md_path, CLAUDE_CODE_INSTRUCTIONS)
    report.append(CopiedItem(
        kind="claude-instructions",
        name="CLAUDE.md",
        source="(generated)",
        target=str(claude_md_path),
        operation="add",
    ))


def build_copilot_parts(
    repo_root: Path,
    output_root: Path,
    skills_manifest: Path,
    agents_manifest: Path,
    hooks_manifest: Path,
) -> tuple[list[CopiedItem], list[str], list[str]]:
    """Build Copilot-only parts into output_root. Returns (report, warnings, mcp_servers)."""
    skills_target = output_root / ".github" / "skills"
    agents_target = output_root / ".github" / "agents"
    hooks_target = output_root / ".github" / "hooks"
    skills_target.mkdir(parents=True, exist_ok=True)
    agents_target.mkdir(parents=True, exist_ok=True)
    hooks_target.mkdir(parents=True, exist_ok=True)

    report: list[CopiedItem] = []
    warnings: list[str] = []

    apply_manifest(repo_root, skills_manifest, "skill", skills_target, report, warnings)
    apply_manifest(repo_root, agents_manifest, "agent", agents_target, report, warnings)
    apply_manifest(repo_root, hooks_manifest, "hook", hooks_target, report, warnings)
    mcp_servers = package_mcp_configuration(repo_root, output_root, report, warnings)
    write_copilot_instructions(output_root, report)
    return report, warnings, mcp_servers


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_root = (repo_root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    dist_dir = output_root.parent
    skills_manifest = (repo_root / args.skills_manifest).resolve()
    agents_manifest = (repo_root / args.agents_manifest).resolve()
    hooks_manifest = (repo_root / args.hooks_manifest).resolve()

    # Clean up old single-bundle output if it exists
    if output_root.exists():
        reset_path(output_root)
    old_zip = output_root.with_suffix(".zip")
    if old_zip.exists():
        old_zip.unlink()

    # --- 1. Build copilot-only bundle ---
    copilot_dir = dist_dir / "copilot-workspace-copilot"
    reset_path(copilot_dir)
    copilot_report, warnings, mcp_servers = build_copilot_parts(
        repo_root, copilot_dir, skills_manifest, agents_manifest, hooks_manifest,
    )
    write_bundle_readme(
        copilot_dir, "copilot",
        copilot_dir / ".github" / "skills",
        copilot_dir / ".github" / "agents",
        copilot_dir / ".github" / "hooks",
        mcp_servers, copilot_report, warnings,
    )
    copilot_zip = create_zip(copilot_dir)

    # --- 2. Build both (copilot + claude) bundle ---
    both_dir = dist_dir / "copilot-workspace-both"
    reset_path(both_dir)
    copy_tree(copilot_dir, both_dir)
    both_report = list(copilot_report)
    both_warnings = list(warnings)
    package_claude_code_workspace(
        both_dir,
        both_dir / ".github" / "skills",
        both_dir / ".github" / "agents",
        both_dir / ".github" / "hooks",
        both_dir / ".vscode" / "mcp.json",
        both_report, both_warnings,
    )
    write_bundle_readme(
        both_dir, "both",
        both_dir / ".github" / "skills",
        both_dir / ".github" / "agents",
        both_dir / ".github" / "hooks",
        mcp_servers, both_report, both_warnings,
    )
    both_zip = create_zip(both_dir)

    # --- 3. Build claude-only bundle ---
    claude_dir = dist_dir / "copilot-workspace-claude"
    reset_path(claude_dir)
    claude_report: list[CopiedItem] = []
    claude_warnings: list[str] = []
    package_claude_code_workspace(
        claude_dir,
        copilot_dir / ".github" / "skills",
        copilot_dir / ".github" / "agents",
        copilot_dir / ".github" / "hooks",
        copilot_dir / ".vscode" / "mcp.json",
        claude_report, claude_warnings,
    )
    claude_skills = claude_dir / ".claude" / "skills"
    claude_agents = claude_dir / ".claude" / "agents"
    write_bundle_readme(
        claude_dir, "claude",
        claude_skills if claude_skills.is_dir() else copilot_dir / ".github" / "skills",
        claude_agents if claude_agents.is_dir() else copilot_dir / ".github" / "agents",
        None,
        mcp_servers, claude_report, claude_warnings,
    )
    claude_zip = create_zip(claude_dir)

    print(f"Copilot-only: {copilot_zip}")
    print(f"Claude-only:  {claude_zip}")
    print(f"Both:         {both_zip}")
    if warnings:
        print(f"Completed with {len(warnings)} warning(s). See BUILD_MANIFEST.json files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())