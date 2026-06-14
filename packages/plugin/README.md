# @research-copilot/plugin

Research Copilot plugin for Claude Code - AI-powered research automation with skills and agents.

## Installation

This plugin is automatically installed when you run:

```bash
rc init
```

The installation happens via the `research-init` command, which:
1. Detects your Claude Code CLI platform
2. Installs the plugin to the appropriate location
3. Creates necessary configuration files

## Manual Installation

If needed, you can also install manually:

```bash
npm install -g @research-copilot/plugin
```

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
