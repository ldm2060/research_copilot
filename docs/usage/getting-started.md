# Getting Started with Research Copilot

Research Copilot is a research-native CLI tool (`rc`) that helps you run academic research as a controlled, stateful workflow. This guide will walk you through installation, setup, and your first research task.

## Prerequisites

- Node.js 18 or higher
- Claude Code (or another supported platform)
- A research project directory

## Installation

### Quick Start (Recommended)

Install globally with npm:

```bash
npm install -g @research-copilot/cli
```

Verify installation:

```bash
rc --version
```

### Alternative Installation Methods

**Using pnpm:**
```bash
pnpm add -g @research-copilot/cli
```

**Using Yarn:**
```bash
yarn global add @research-copilot/cli
```

**Without Installation (npx):**
```bash
npx @research-copilot/cli init --user your-name --claude
```

## First-Time Setup

### 1. Initialize Your Research Project

Navigate to your research project directory and run:

```bash
rc init --user your-name --claude
```

This command:
- Creates a `.research/` directory with the workflow structure
- Sets up Claude Code integration (with `--claude` flag)
- Scaffolds template directories for specs, tasks, and workspace
- Configures the injection hook for Claude Code

Verify the setup:

```bash
rc doctor
```

You should see:
```
OK  .research/ exists
OK  workflow.md exists
OK  .claude/settings.json exists
```

### 2. Understanding the Structure

After initialization, your project will have:

```
your-project/
├── .research/
│   ├── tasks/           # Task definitions and state
│   ├── spec/            # Research specifications
│   │   ├── venue/
│   │   ├── writing/
│   │   ├── baselines/
│   │   ├── methodology/
│   │   └── novelty/
│   ├── workspace/       # Working artifacts
│   ├── .runtime/        # Runtime state
│   ├── workflow.md      # Workflow guidance
│   └── config.yaml      # Configuration
└── .claude/
    ├── settings.json    # Claude Code hook configuration
    └── agents/          # Research agent templates
```

## Your First Research Task

### 1. Check Current State

Before creating any tasks:

```bash
rc context
```

Output:
```
[workflow-state:no_task]
No active task. Create one with: rc task create --kind <k> --title "<t>"
[/workflow-state]

[research-state]
Active: none
Graph: 0 completed · 0 in_progress · 0 blocked
```

### 2. Create a Literature Review Task

```bash
rc task create --kind literature --title "Survey transformer architectures" --venue ICML
```

This returns a task ID like:
```
2026-06-06-survey-transformer-architectures
```

**Available task kinds:**
- `literature` — Reading papers, surveys
- `ideation` — Brainstorming, hypothesis generation
- `experiment` — Running experiments, collecting data
- `writing` — Drafting papers, sections
- `polish` — Editing, formatting, finalizing
- `review` — Peer review, feedback incorporation
- `rebuttal` — Responding to reviews

### 3. Check the Active Task

```bash
rc task current
```

Output:
```
2026-06-06-survey-transformer-architectures
```

### 4. View Workflow State

```bash
rc context
```

Now you'll see:
```
[workflow-state:planning]
Active task is in PLANNING. Use the rc-plan helper to clarify it into prd.md 
and curate execute.jsonl / verify.jsonl. Then: rc task start <id>
[/workflow-state]

[research-state]
Active: 2026-06-06-survey-transformer-architectures (literature, planning)
Graph: 0 completed · 0 in_progress · 0 blocked
Recommended next:
  1. resume literature task 2026-06-06-survey-transformer-architectures (planning)
```

### 5. Start Working on the Task

Move the task from planning to in-progress:

```bash
rc task start 2026-06-06-survey-transformer-architectures
```

The workflow state changes:
```bash
rc context
```

```
[workflow-state:in_progress]
Active task is IN PROGRESS. Dispatch the rc-literature executor with prd.md + 
execute.jsonl specs. Do NOT do domain work inline. When done: rc task verify <id>
[/workflow-state]
```

### 6. Work with Claude Code

With Claude Code integration, the workflow state is automatically injected into every conversation turn. Simply ask Claude to help with your task:

```
"Help me survey recent transformer papers for ICML"
```

Claude will see the workflow state and guide you according to the research lifecycle.

### 7. Verify Your Work

When you've completed the task work, move it to the verify gate:

```bash
rc task set-status 2026-06-06-survey-transformer-architectures verify
rc task verify 2026-06-06-survey-transformer-architectures
```

If verification passes:
```
verify OK for 2026-06-06-survey-transformer-architectures
```

If it fails, the task automatically rolls back to `in_progress` for fixes.

### 8. Complete the Task

After passing verification:

```bash
rc task complete 2026-06-06-survey-transformer-architectures
```

Check your progress:
```bash
rc context
```

```
[research-state]
Active: none
Graph: 1 completed · 0 in_progress · 0 blocked
Recommended next:
  (recommendations based on completed work and open gaps)
```

## Common Workflows

### Creating a Child Task

Create a follow-up task that depends on another:

```bash
rc task create --kind experiment \
  --title "Implement baseline model" \
  --parent 2026-06-06-survey-transformer-architectures
```

### Recording Research Gaps

When you discover missing work:

```bash
rc task add-gap 2026-06-06-survey-transformer-architectures \
  --desc "Need ablation study on attention heads" \
  --suggest experiment
```

This gap will appear in recommendations:
```
Open gaps:
  - [from 2026-06-06-survey...] Need ablation study -> suggests: experiment
Recommended next:
  2. create experiment task to resolve "Need ablation study..."
```

### Checking Task Status

View all tasks:
```bash
rc task list
```

Set task status explicitly:
```bash
rc task set-status <task-id> <status>
```

Valid statuses: `planning`, `in_progress`, `verify`, `completed`

## Integration with Claude Code

The `rc context` command runs automatically on every Claude Code conversation turn via the `UserPromptSubmit` hook. This provides:

1. **Workflow State** — Guidance for the current lifecycle phase
2. **Research State** — Active task, graph overview, recommendations
3. **Deterministic Next Steps** — Computed from task graph and gaps

You don't need to manually run `rc context` when using Claude Code — it happens automatically.

## Updating Research Copilot

Check your installed version:
```bash
rc --version
```

Update to the latest version:
```bash
npm update -g @research-copilot/cli
```

Or reinstall:
```bash
npm install -g @research-copilot/cli@latest
```

## Next Steps

- **[Command Reference](commands.md)** — Detailed documentation for all `rc` commands
- **[Workflow Walkthrough](workflow-walkthrough.md)** — A complete example from init to completion
- **[Claude Code Setup](claude-code.md)** — Platform-specific configuration details

## Troubleshooting

### rc command not found

Ensure npm global bin directory is in your PATH:
```bash
npm config get prefix
```

Add `<prefix>/bin` (Unix) or `<prefix>` (Windows) to your PATH.

### .research/ directory not found

Make sure you're in the project root where you ran `rc init`, or specify the path:
```bash
rc task create --repo /path/to/project --kind literature --title "..."
```

### Hook not triggering in Claude Code

Verify the hook is configured:
```bash
rc doctor
```

Check `.claude/settings.json` contains:
```json
{
  "hooks": {
    "UserPromptSubmit": "rc context --event UserPromptSubmit --format json"
  }
}
```

## Getting Help

- **GitHub Issues**: https://github.com/ldm2060/research_copilot/issues
- **Documentation**: https://github.com/ldm2060/research_copilot/tree/main/docs
- **Command Help**: `rc --help`
