# Research Copilot

Academic research workspace for Claude Code: paper writing, review, literature search, experiment management, and AI Scientist workflow.

## Install

### Step 1: Add dependency marketplaces

This plugin depends on skills from 5 third-party marketplaces. You must add them before installing, or dependency plugins may stay unresolved. The `superpowers` dependency uses Claude Code's built-in `claude-plugins-official` marketplace.

```
/plugin marketplace add Imbad0202/academic-research-skills
/plugin marketplace add Lylll9436/Paper-Polish-Workflow-skill
/plugin marketplace add multica-ai/andrej-karpathy-skills
/plugin marketplace add anthropics/skills
/plugin marketplace add Orchestra-Research/AI-Research-SKILLs
/plugin install academic-research-skills@academic-research-skills
/plugin install paper-polish-workflow@paper-polish-workflow
/plugin install andrej-karpathy-skills@karpathy-skills
/plugin install superpowers@claude-plugins-official
/plugin install example-skills@anthropic-agent-skills
/plugin install ml-paper-writing@ai-research-skills
/plugin install autoresearch@ai-research-skills
```

### Step 2: Install the plugin

From GitHub:

```bash
/plugin marketplace add https://github.com/ldm2060/research_copilot.git
/plugin install research-copilot@research-copilot
/reload-plugins
```

From Gitee (China mirror):

```bash
/plugin marketplace add https://gitee.com/ldm2060/research_copilot.git
/plugin install research-copilot@research-copilot
/reload-plugins
```

## Update

```bash
/plugin marketplace update research-copilot
/reload-plugins
```

## Components

- **320+ skills**: paper writing, review, literature search, experiment design, plotting, LaTeX, and more
- **10 agents**: research-pilot (full lifecycle), paper (routing + optimization), paper-writer, paper-reviewer, scientist (AI-Scientist-v2), and more
- **6 MCP servers**: arxiv-search, dblp-bib, google-scholar, pdf-text, ai-scientist, arxivsub-search
- **1 hook**: SessionStart guardrails

## Post-install

After installing, run this once to set up MCP server dependencies:

```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/requirements.txt
```

## Quick start

| I want to... | Use |
|---|---|
| Start from scratch (find direction / baseline / innovation) | `@research-pilot` |
| Work on an existing draft (revise / review / optimize) | `@paper` |
| Write or polish a section | `@paper-writer` |
| Pre-submission quality gate / rebuttal | `@paper-reviewer` |
| AI Scientist automated workflow | `@scientist` |
| Search papers | `arxiv-search` or `dblp-bib` MCP |
| Extract text from PDF | `pdf-text` MCP |

## For developers

If you want to build from source or contribute:

```bash
git clone --recurse-submodules https://github.com/ldm2060/research_copilot.git
python scripts/build_copilot_workspace.py --repo-root . --output dist/claude-workspace --target github
```

Build targets: `--target github` or `--target gitee`.
