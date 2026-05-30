# Research Copilot

Academic research workspace for Claude Code: paper writing, review, literature search, experiment management, and AI Scientist workflow.

## Install

### Prerequisite: add the dependency marketplaces

This plugin depends on six third-party plugins. Add their marketplaces **before** installing, or the dependencies will stay unresolved:

```bash
claude plugin marketplace add Imbad0202/academic-research-skills
claude plugin marketplace add Lylll9436/Paper-Polish-Workflow-skill
claude plugin marketplace add forrestchang/andrej-karpathy-skills
claude plugin marketplace add obra/superpowers
claude plugin marketplace add anthropics/skills
claude plugin marketplace add Orchestra-Research/AI-Research-SKILLs
```

Then install research-copilot as usual; Claude Code resolves and installs the dependencies automatically.

### From GitHub

```bash
/plugin marketplace add https://github.com/ldm2060/research_copilot.git
/plugin install research-copilot@research-copilot
/reload-plugins
```

### From Gitee (China mirror)

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

After installing, run this once to set up MCP dependencies:

```bash
python ${CLAUDE_PLUGIN_ROOT}/requirements.txt
```

Or let the plugin handle it automatically on first use.

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
