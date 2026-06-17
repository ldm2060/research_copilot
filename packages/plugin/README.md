# @research-copilot/plugin

Research Copilot plugin for Claude Code - AI-powered research automation with skills and agents.

## Installation

Most users should install the Research Copilot CLI, then let `rc init` or `rc doctor --fix` synchronize this companion plugin package:

```bash
npm install -g @research-copilot/cli
rc init --user your-name --claude
rc doctor
```

For an existing Research Copilot project after upgrading the CLI:

```bash
npm install -g @research-copilot/cli@latest
rc doctor --fix
rc doctor
```

`rc init` and `rc doctor --fix` are idempotent: they preserve existing tasks, specs, workspace files, user hooks, user agents, and unrelated MCP servers.

## Manual Plugin Synchronization

If `rc doctor` reports a plugin version mismatch, install the exact version it prints:

```bash
npm install -g @research-copilot/plugin@<cli-version>
```

This npm package is a companion package for plugin content and version synchronization. Project-local Claude Code configuration created by `rc init` remains the reliable runtime path, so npm global installation alone is not the only Research Copilot activation step.

## What's Included

### Skills (6 total)

1. **deep-research** - Multi-source web research with adversarial fact-checking
2. **academic-search** - Search academic papers across multiple databases
3. **literature-review** - Generate comprehensive literature reviews
4. **citation-manager** - Manage citations and bibliographies
5. **data-analysis** - Analyze research data with statistical methods
6. **report-generator** - Generate formatted research reports

### Agents (10 total)

Specialized AI agents for different research tasks:
- Literature review agent
- Data collection agent
- Analysis agent
- Citation agent
- Summary agent
- Fact-checking agent
- Writing agent
- Methodology agent
- Survey design agent
- Meta-analysis agent

### Commands

- `/research-init` - Initialize research environment
- `/search-papers` - Quick academic paper search
- `/cite` - Generate citations
- `/analyze` - Run data analysis

## Usage

After installation, all skills and agents are available in Claude Code:

```bash
# Use a skill
/deep-research "impact of AI on scientific research"

# Run the literature review agent
@literature-review "summarize recent ML papers"
```

## Requirements

- Claude Code CLI (any supported platform)
- Node.js >= 18
- Internet connection for web research features

## Configuration

Plugin settings can be customized in `.claude/research-copilot.local.md`

## License

MIT
