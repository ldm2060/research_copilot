---
name: validate-plugin-build
description: Build the research-copilot plugin workspace and verify the output is publishable. Use before tagging a release, after editing skills/agents/MCP servers, or when troubleshooting plugin discovery issues. Runs scripts/build_copilot_workspace.py for both targets (github + gitee), then checks skill.json coverage, agent frontmatter, and MCP server entry points.
disable-model-invocation: true
---

# validate-plugin-build

End-to-end pre-release check for the research-copilot plugin. Run this **before** pushing a release branch or updating the marketplace.

## When to use

- Before tagging a release on `deploy` branch
- After bulk edits to `self/skills/`, `self/agents/`, or `self/mcp/`
- When users report missing skills / agents after `/plugin install`
- When CI fails to build the dist artifact

## Workflow

### 1. Clean previous build

```bash
rm -rf dist/claude-workspace
```

### 2. Build both targets

```bash
python scripts/build_copilot_workspace.py --repo-root . --output dist/claude-workspace --target github
python scripts/build_copilot_workspace.py --repo-root . --output dist/claude-workspace-gitee --target gitee
```

### 3. Verify skill.json coverage

Every `SKILL.md` must have a sibling `skill.json` (Claude Code 2.1.142+ requirement).

```bash
python self/scripts/generate-skill-json.py --root self/skills --check
python self/scripts/generate-skill-json.py --root dist/claude-workspace/skills --check
```

If `--check` exits non-zero, run without `--check` to regenerate, then commit the changes.

### 4. Verify MCP servers handshake

```bash
python self/install.py --dry-run --skip-deps
```

Then run a real handshake (writes nothing):

```bash
python -c "from self.install import build_mcp_config, verify_mcp_servers; from pathlib import Path; verify_mcp_servers(build_mcp_config(Path('.')))"
```

All 6 servers should report `OK`. If any report `FAIL`, dispatch the `mcp-handshake-tester` agent for deeper diagnosis.

### 5. Verify agent + plugin manifests

```bash
ls dist/claude-workspace/agents/*.md | wc -l   # should match self/agents/*.agent.md count
test -f dist/claude-workspace/.claude-plugin/marketplace.json || echo "MISSING marketplace.json"
```

### 6. Verify dual-source parity

GitHub and Gitee builds should differ **only** in remote URLs / mirror-specific paths:

```bash
diff -r dist/claude-workspace dist/claude-workspace-gitee | grep -v "github.com\|gitee.com"
```

Output should be empty (or only mirror-related differences).

## Pass criteria

- Both build commands exit 0
- `generate-skill-json.py --check` exits 0 for both source and dist
- All MCP servers report `OK` in handshake
- Agent count in dist matches source
- Dual-source diff contains only mirror URL differences

## Failure recovery

| Symptom | Action |
|---------|--------|
| Build fails on submodule | `git submodule update --init --recursive`, then retry |
| skill.json missing | Run generator without `--check`, commit the new files |
| MCP server FAIL | Check `python -u <server.py>` directly for stack trace |
| Agent missing in dist | Confirm filename is `<name>.agent.md`, not `<name>.md` |

## Related

- Submodule sync issues → use `sync-submodules` skill
- Per-component validation → dispatch `plugin-component-validator` agent
- MCP-only verification → dispatch `mcp-handshake-tester` agent
