# Platform Plugin Registration Design

- **Date**: 2026-06-19
- **Status**: Design approved
- **Problem**: `@research-copilot/plugin` can be synchronized through npm, but there is no `rc` command that registers the plugin content with Claude Code, Codex, Gemini, Cursor, OpenCode, or Windsurf discovery paths. As a result, `rc doctor` can report that Claude Code is available but does not list `research-copilot` even though standalone project configuration works.
- **Solution**: Add an explicit `rc plugin` command group that separates npm package synchronization from platform plugin registration.
- **Related**: Refines `docs/superpowers/specs/2026-06-17-plugin-cli-integration-design.md` by adding the missing platform registration layer.

---

## 1. Goals

1. Provide a clear command that connects `@research-copilot/plugin` to supported platform discovery paths.
2. Keep npm package synchronization and platform registration as separate concepts.
3. Support Claude Code first, then Codex, Gemini, Cursor, OpenCode, and Windsurf through the existing platform registry.
4. Make registration idempotent: re-running the command updates Research Copilot-managed plugin content without duplicating entries or deleting unrelated user content.
5. Support both project-local registration and user-global registration where a platform supports both.
6. Give `rc doctor` a precise remediation command when a platform does not list or discover the plugin.

## 2. Non-goals

1. Do not remove the existing standalone configuration path created by `rc init`.
2. Do not require Claude Code marketplace setup for normal Research Copilot use.
3. Do not make `npm install -g @research-copilot/plugin` imply platform discovery.
4. Do not overwrite unrelated platform plugins, user agents, user skills, rules, hooks, or MCP entries.
5. Do not add `rc upgrade`; `rc doctor --fix` remains the explicit old-project repair path.

---

## 3. Command Surface

Add a new top-level command group:

```bash
rc plugin install [--platform <claude|codex|gemini|cursor|opencode|windsurf|all|configured>] [--scope project|user] [--source npm|local] [--path <dist>]
rc plugin status  [--platform <claude|codex|gemini|cursor|opencode|windsurf|all|configured>] [--scope project|user]
rc plugin update  [--platform <claude|codex|gemini|cursor|opencode|windsurf|all|configured>] [--scope project|user] [--source npm|local] [--path <dist>]
rc plugin remove  [--platform <claude|codex|gemini|cursor|opencode|windsurf|all|configured>] [--scope project|user]
```

Defaults:

```bash
rc plugin install
```

is equivalent to:

```bash
rc plugin install --platform claude --scope project --source npm
```

Platform alias rules:

- `claude` maps to registry id `claude-code`.
- `all` means every platform in `AI_TOOLS`.
- `configured` means platforms with existing project config directories or files in the current repo, such as `.claude/`, `.codex/`, `.gemini/`, `.cursor/`, `.opencode/`, or `.windsurf/`.

---

## 4. Source Resolution

The command must resolve plugin content before registration.

### npm source

```bash
rc plugin install --source npm
```

Steps:

1. Read the CLI version.
2. Ensure `@research-copilot/plugin@<cliVersion>` is installed through existing plugin sync logic.
3. Resolve the global npm package root.
4. Use `<packageRoot>/dist` as the plugin content source.

If package root resolution fails, print an actionable command:

```bash
npm install -g @research-copilot/plugin@<cliVersion>
```

### local source

```bash
rc plugin install --source local --path packages/plugin/dist
```

Steps:

1. Resolve `--path` relative to the current repo.
2. Verify the directory exists.
3. Verify it contains at least one platform metadata directory such as `.claude-plugin/` or `.codex-plugin/` and content directories such as `skills/`, `agents/`, or `hooks/`.

Local source is for development and dogfooding.

---

## 5. Registration Model

Registration copies or links plugin content into each platform's plugin or skill discovery location. The first implementation should copy content rather than symlink it, because copying works consistently on Windows, macOS, Linux, CI, and restricted shells.

Each registration target is a directory named `research-copilot` under the selected platform's discovery path.

Example:

```text
<targetRoot>/research-copilot/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.toml
  agents/
  skills/
  hooks/
```

The command may copy the whole `dist/` tree for simplicity. Platform-specific status checks then inspect only the metadata relevant to that platform.

Idempotency rules:

1. If `research-copilot/` already exists and contains Research Copilot metadata, replace its Research Copilot-managed contents.
2. If `research-copilot/` exists but does not contain Research Copilot metadata, fail with a clear message instead of overwriting.
3. Do not modify sibling plugin directories.
4. Do not delete user-owned platform files outside the `research-copilot/` registration target.

---

## 6. Platform Targets

Use `AI_TOOLS` as the source of platform ids and project-local discovery paths.

### Claude Code

Project scope:

```text
<repo>/.claude/skills/research-copilot/
```

User scope:

```text
~/.claude/skills/research-copilot/
```

Expected status after project registration:

```bash
claude plugin list
```

should list `research-copilot` if the installed Claude Code version supports skills-directory plugin discovery for that scope. If it does not, `rc plugin status` should still report the directory registration as OK and explain that Claude Code did not list it.

### Codex

Project scope:

```text
<repo>/.agents/skills/research-copilot/
```

User scope is not enabled in the first implementation unless Codex user-scope discovery is documented in this repo.

### Gemini

Project scope installs to both known skill paths from the registry:

```text
<repo>/.gemini/skills/research-copilot/
<repo>/.agents/skills/research-copilot/
```

Both paths are idempotent and safe to re-run.

### Cursor

Project scope:

```text
<repo>/.cursor/skills/research-copilot/
```

### OpenCode

Project scope:

```text
<repo>/.opencode/skills/research-copilot/
```

### Windsurf

Windsurf is agent-less and currently uses workflows/rules. The first implementation should register plugin content under:

```text
<repo>/.windsurf/workflows/research-copilot/
```

If Windsurf plugin discovery becomes documented in a future release, add that path as an additional Windsurf target behind the same `rc plugin install --platform windsurf` command surface.

---

## 7. Status Output

`rc plugin status --platform all` should report three layers when relevant:

1. npm package sync status.
2. project/user registration directory status.
3. platform-native listing status, if a native command exists and is safe to run.

Example:

```text
Claude Code
  npm package: OK @research-copilot/plugin@1.1.18
  project plugin: OK .claude/skills/research-copilot
  claude plugin list: OK research-copilot

Codex
  npm package: OK @research-copilot/plugin@1.1.18
  project plugin: MISSING .agents/skills/research-copilot
  fix: rc plugin install --platform codex --scope project
```

For current `rc doctor`, replace the vague plugin-list INFO with:

```text
INFO Claude Code is available but does not list research-copilot plugin.
Standalone configuration can still work.
To register the npm plugin, run: rc plugin install --platform claude --scope project
```

---

## 8. Relationship to `rc init` and `rc doctor`

`rc init` remains responsible for standalone project configuration. It should not silently perform user-global plugin registration.

Add an explicit init option:

```bash
rc init --user <name> --claude --install-plugin
```

This option runs:

```bash
rc plugin install --platform claude --scope project
```

after standalone configuration and npm sync succeed or warn according to existing strictness rules.

Without `--install-plugin`, `rc init` should print a concise next-step hint when Claude Code is selected:

```text
To register the npm plugin with Claude Code, run:
  rc plugin install --platform claude --scope project
```

`rc doctor --fix` remains focused on repairing standalone config and npm sync. It may print plugin registration remediation but should not install platform plugins unless a future `--install-plugin` flag is added to doctor.

---

## 9. Error Handling

- Missing npm package root: warn or fail with `npm install -g @research-copilot/plugin@<cliVersion>` depending on command strictness.
- Missing local `--path`: fail.
- Unsupported platform: fail and list valid platform names.
- User scope requested for a platform without user-scope support: fail with a clear message.
- Existing non-Research-Copilot target directory: fail and do not overwrite.
- Partial multi-platform install: continue installing other platforms, then return non-zero with a summary of failures.

---

## 10. Tests

### Unit tests

- Platform alias resolution: `claude` → `claude-code`, `all`, `configured`.
- Source resolution for `npm` and `local`.
- Refuse to overwrite an existing non-Research-Copilot target directory.
- Idempotently replace an existing Research Copilot target directory.
- Claude project scope writes `.claude/skills/research-copilot`.
- Claude user scope writes under a fake home directory.
- Gemini project scope writes both `.gemini/skills/research-copilot` and `.agents/skills/research-copilot`.
- Unsupported user scope for non-Claude platforms fails clearly.

### CLI tests

- `rc plugin install --platform claude --scope project --source local --path <dist>` succeeds.
- `rc plugin status --platform claude` reports missing before install and OK after install.
- `rc plugin remove --platform claude --scope project` removes only the `research-copilot` registration target.
- `rc init --install-plugin --claude` invokes plugin registration after init.
- `rc doctor` prints `rc plugin install --platform claude --scope project` as remediation when Claude Code does not list the plugin.

---

## 11. Rollout

1. Implement `packages/cli/src/commands/plugin-register.ts` for source resolution, platform target resolution, install/status/remove operations, and structured results.
2. Add `packages/cli/src/commands/plugin-command.ts` to wire Commander subcommands.
3. Update `program.ts` to register the `plugin` command group.
4. Add `--install-plugin` to `rc init` and call the registration helper explicitly.
5. Update `rc doctor` remediation text to point to `rc plugin install`.
6. Add tests and update docs.

This completes the missing layer: npm package sync says the plugin package exists; platform registration says the target CLI can discover it.
