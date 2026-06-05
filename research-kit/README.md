# Research Kit

Core research agents and task specifications for academic workflows.

## Contents

### Agents (research-kit/agents/)

Research agents that help with academic work:

1. **rc-ideation** - Brainstorms research directions, analyzes novelty, generates cross-domain analogies
2. **rc-literature** - Searches papers, locks baselines, builds related-work map
3. **rc-experiment** - Designs and runs experiments, extracts metrics, judges results
4. **rc-writer** - Drafts LaTeX paper sections from experiment artifacts
5. **rc-reviewer** - Simulates top-venue reviewer, produces review reports
6. **rc-rebuttal** - Parses reviewer comments and drafts evidence-driven responses
7. **rc-polisher** - Polishes language and removes AI-tells without changing technical content
8. **rc-plan** - Clarifies tasks into prd.md and curates execute/verify specs
9. **rc-verify** - Runs quality gates (number/citation traceability, de-AI checks)
10. **rc-update-spec** - Promotes learnings into .research/spec/

### Spec Templates (research-kit/spec-templates/)

Task specification templates for common research workflows:

- **baselines/** - Baseline method definitions
- **methodology/** - Experimental methodology templates
- **novelty/** - Novelty analysis frameworks
- **venue/** - Venue-specific requirements and guidelines
- **writing/** - Writing style guides and templates

## Usage

Research agents are loaded automatically by research-copilot when you run `rc init` on a repository with `skillpacks.yaml` configured.

### Platform Integration

After running `rc sync`, agents are installed to your AI platform's agent directory:

- **Claude Code**: `.claude/agents/*.md`
- **Codex**: `.codex/agents/*.toml`
- **OpenCode**: `.opencode/agent/*.md`
- **Gemini**: `.gemini/agents/*.md`
- **Cursor**: `.cursor/rules/research-copilot.md` (breadcrumb protocol)
- **Windsurf**: `.windsurf/workflows/rc-*.md` (workflows)

## Development

This is a skillpack managed by research-copilot. To contribute:

1. Edit agent files in `agents/*.md`
2. Follow frontmatter schema (name, description, kind, model)
3. Test with `rc sync --repo <test-repo> --target-dir <output>`

## License

MIT
