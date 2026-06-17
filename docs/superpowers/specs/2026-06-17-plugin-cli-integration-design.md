# Plugin CLI Integration Design

- **Date**: 2026-06-17
- **Status**: Design approved
- **Problem**: `@research-copilot/plugin` is now published to npm, but the `rc` CLI needs a complete, safe integration story for installation, version synchronization, runtime loading checks, and upgrades from older Research Copilot installs.
- **Solution**: Keep the existing project-local Research Copilot configuration as the reliable runtime path, and add npm plugin synchronization plus diagnostic loading checks as an idempotent enhancement.
- **Related**: This refines the integration and migration sections of `docs/superpowers/specs/2026-06-14-cross-platform-plugin-package-design.md`.

---

## 1. Goals

1. `rc init` should work for both new projects and older Research Copilot projects.
2. Users upgrading from older versions should not need to delete `.research/`, `.claude/`, or MCP configuration.
3. The npm plugin package should be installed or updated to match the CLI version when Claude Code support is enabled.
4. `rc doctor` should distinguish between core project failures and plugin-related warnings.
5. The integration should be safe, idempotent, and reversible: merge missing Research Copilot-managed entries, preserve user-owned configuration, and avoid destructive rewrites.

## 2. Non-goals

1. Do not require Claude Code marketplace setup before Research Copilot can function.
2. Do not make `npm install -g @research-copilot/plugin` the only loading mechanism; npm global install alone does not make Claude Code load a plugin.
3. Do not overwrite user hooks, user agents, existing `.research/tasks`, specs, workspace files, or unrelated MCP entries.
4. Do not block `rc init` solely because npm plugin installation or Claude Code plugin inspection fails.

---

## 3. Integration Model

Research Copilot should use a **dual-track integration**.

### Track A: Project-local standalone configuration

This is the required runtime path. `rc init` reconciles the project into this desired state:

- `.research/` directories exist.
- `.research/workflow.md` and `.research/config.yaml` exist and match the current kit where safe.
- `.claude/settings.json` contains the Research Copilot `UserPromptSubmit` hook that calls `rc context`.
- `.claude/agents/` contains the expected `rc-*` agents.
- `.mcp.json` contains the Research Copilot MCP server entries while preserving unrelated MCP entries.
- `CLAUDE.md` contains the Research Copilot workflow instruction block while preserving unrelated project instructions.

This track is what makes Research Copilot work even if plugin marketplace loading is unavailable.

### Track B: npm plugin synchronization and loading diagnostics

This is an enhancement for packaging, version visibility, and eventual platform plugin discovery.

When Claude Code support is enabled, `rc init` should synchronize `@research-copilot/plugin` to the CLI version:

- If the plugin is missing, install `@research-copilot/plugin@<cliVersion>`.
- If the plugin version differs from the CLI version, install `@research-copilot/plugin@<cliVersion>`.
- If the plugin version matches, skip installation.
- If npm installation fails, continue after emitting a warning and the exact manual remediation command.

If the `claude` CLI is available, `rc init` and `rc doctor` should inspect `claude plugin list` when the command is supported to report whether Claude Code sees a Research Copilot plugin. This check is informational by default because standalone configuration remains the supported runtime path.

---

## 4. `rc init` Behavior

`rc init` becomes an idempotent **initialize or reconcile** command.

### New project

For a fresh repository, `rc init --user <name> --claude` should:

1. Create `.research/` structure.
2. Write default workflow and config files.
3. Configure Claude Code hooks, agents, MCP, and instructions.
4. Install or update `@research-copilot/plugin@<cliVersion>`.
5. Print a concise summary of what was created, updated, skipped, or warned.

### Existing project / upgrade from older versions

For an older Research Copilot project, re-running `rc init` should reconcile missing or outdated managed pieces without deleting user state:

1. Preserve `.research/tasks`, `.research/spec`, `.research/workspace`, and `.research/runtime` contents.
2. Merge the current hook into `.claude/settings.json` if missing or outdated.
3. Refresh Research Copilot-managed `rc-*` agents to the current shipped content.
4. Preserve non-Research-Copilot agents and hooks.
5. Merge or repair Research Copilot MCP entries without removing unrelated MCP entries.
6. Sync `@research-copilot/plugin` to the CLI version.
7. Emit a summary explaining that this was a safe upgrade/reconcile, not a destructive reinitialization.

The user-facing upgrade guidance should be:

```bash
npm install -g @research-copilot/cli@latest
rc init --user <name> --claude
rc doctor
```

If a more explicit upgrade command is added, it should call the same reconcile logic rather than duplicating behavior.

### Init options

Add these options:

- `--skip-plugin`: skip npm plugin install/update. Useful for offline work, CI, or locked-down machines.
- `--strict-plugin`: treat plugin install/update failure as an initialization failure. Default is non-strict.

---

## 5. `rc doctor` Behavior

`rc doctor` should report in three sections.

### Core project config

These checks determine the default exit code:

- `.research/` exists.
- `.research/workflow.md` exists.
- `.research/config.yaml` exists.
- `.claude/settings.json` exists when Claude Code support is configured.
- `.claude/settings.json` contains a Research Copilot hook with `rc context`.
- `.claude/agents/` contains the expected `rc-*` agents.
- `.mcp.json` contains expected Research Copilot MCP server entries.
- `CLAUDE.md` contains the Research Copilot workflow instruction.

Missing or invalid core config is `FAIL`.

### NPM plugin

These checks are warnings by default:

- `@research-copilot/plugin` is globally installed.
- Installed plugin version equals the CLI version.
- On mismatch, print the exact fix command:

```bash
npm install -g @research-copilot/plugin@<cliVersion>
```

With `rc doctor --strict-plugin`, plugin mismatch or missing plugin becomes a failure.

### Claude Code plugin loading

These checks are informational by default:

- `claude` CLI is available.
- `claude plugin list` can run.
- Research Copilot appears in the plugin list, if the current Claude Code version exposes plugin listing.

If Research Copilot is not listed, doctor should explain that standalone configuration can still work and point users to the plugin-specific remediation path if they want Claude Code plugin loading.

### Fix mode

Add `rc doctor --fix` as the explicit old-version upgrade path. It should:

1. Run the same reconcile logic as `rc init` for existing projects.
2. Sync npm plugin unless `--skip-plugin` is also provided.
3. Print a `Fixed:` list and a `Still needs attention:` list.
4. Preserve user-owned config.

Do not add `rc upgrade` in this design. `rc doctor --fix` is the explicit old-version upgrade path; `rc init` remains safe to re-run for users who follow the existing initialization command.

---

## 6. Implementation Boundaries

The implementation should centralize desired-state reconciliation instead of spreading upgrade logic across commands.

Suggested boundaries:

- `readCliVersion()` reads the installed CLI package version.
- `getInstalledPluginVersion()` reads `npm list -g @research-copilot/plugin --json`.
- `syncPluginPackage({ version, strict, skip })` installs only when needed and returns a structured status.
- `reconcileProject({ repo, platforms, user, plugin })` creates or updates Research Copilot-managed files and returns a structured summary.
- `runDoctor({ repo, strictPlugin, fix })` consumes the same checks and optionally invokes reconcile.

The existing platform configurators should remain responsible for platform-local config, but they should be safe to run repeatedly and should preserve foreign configuration.

---

## 7. Error Handling

- Core filesystem/configuration failures should fail `rc init`.
- npm plugin failures should warn by default and fail only with `--strict-plugin`.
- Missing `npm` should warn unless strict plugin mode is active.
- Missing `claude` CLI should warn or inform, not fail default initialization.
- Failed `claude plugin list` should not fail default initialization.
- All warnings must include concrete next commands where possible.

---

## 8. User-Facing Messages

`rc init` should avoid implying that npm global install alone loads a Claude Code plugin. Suggested wording:

```text
Initialized Research Copilot project configuration.
Synced @research-copilot/plugin to 1.1.17.
Standalone Claude Code configuration is ready. Run `rc doctor` to verify plugin and platform status.
```

For upgrades:

```text
Reconciled existing Research Copilot configuration.
Preserved existing tasks, specs, workspace files, and non-Research-Copilot settings.
Updated: rc agents, Claude hook, plugin version.
```

For plugin warning:

```text
Warning: could not install @research-copilot/plugin@1.1.17.
Research Copilot project configuration was still initialized.
To sync the plugin manually, run: npm install -g @research-copilot/plugin@1.1.17
```

---

## 9. Tests

### Init tests

- Fresh `rc init` creates core `.research/` and Claude Code config.
- Re-running `rc init` does not duplicate hooks or MCP entries.
- Re-running `rc init` preserves user hooks and unrelated MCP entries.
- Existing `.research/tasks`, specs, workspace, and runtime files are preserved.
- Missing `rc-*` agents are restored.
- Outdated Research Copilot-managed agents are refreshed.
- Plugin missing triggers install of `@research-copilot/plugin@<cliVersion>`.
- Plugin version mismatch triggers install of `@research-copilot/plugin@<cliVersion>`.
- `--skip-plugin` avoids npm calls.
- Plugin install failure is warning-only by default and failure under `--strict-plugin`.

### Doctor tests

- Core config failures set a non-zero exit code.
- Plugin missing/mismatch is warning-only by default.
- `--strict-plugin` makes plugin missing/mismatch fail.
- `--fix` repairs missing hook, agents, MCP entries, workflow/config files, and plugin mismatch.
- `--fix --skip-plugin` repairs project config without npm calls.
- Doctor output includes manual remediation commands.

---

## 10. Rollout

1. Implement shared reconciliation helpers and tests.
2. Wire `rc init` to use the helpers and add `--skip-plugin` / `--strict-plugin`.
3. Expand `rc doctor` checks and add `--fix` / `--strict-plugin`.
4. Update installation and upgrade docs.
5. Keep the previous standalone behavior working throughout the rollout.

The first release should not force `claude plugin install`; it should make the npm plugin visible, synchronized, and diagnosable while preserving the project-local path that already powers Research Copilot.
