# Cross-Platform Plugin Package Design

- **Date**: 2026-06-14
- **Status**: Design approved
- **Problem**: Skills defined in `research-kit/skills/` are not discoverable by CLI platforms (Claude Code, Cursor, etc.), preventing users from invoking them via slash commands.
- **Solution**: Create `@research-copilot/plugin` npm package that bundles research-kit content with multi-platform metadata for automatic plugin discovery.

---

## 1. Problem Statement

### Current State
- Research Copilot has 6 orchestration skills defined in `research-kit/skills/`:
  - `full-research-workflow` - Complete pipeline (literature → submission)
  - `literature-search` - Focused paper search + baseline locking
  - `experiment-design` - Design and launch experiments
  - `paper-polish` - De-AI and style refinement
  - `submission-sprint` - Iterative review-fix loop
  - `sanity-check` - 6-dimension final audit
- Plus 10 agents in `research-kit/agents/`: `rc-experiment`, `rc-ideation`, etc.
- These are NOT installed to `.claude/skills/` or equivalent platform directories
- Result: Users cannot invoke `/full-research-workflow` or other skills via CLI

### Requirements
1. Skills must be discoverable by **multiple CLI platforms** (Claude Code, Cursor, Codex, Gemini, OpenCode, Windsurf)
2. Distribution via **npm** for easy installation
3. Auto-installation during `rc init --<platform>`
4. Support both end-user installation AND local development (dogfooding)

---

## 2. Architecture: Standalone Plugin Package

### Package Structure

```
packages/plugin/                              # New monorepo package
├── package.json                              # @research-copilot/plugin
│   name: "@research-copilot/plugin"
│   version: synced with @research-copilot/cli
│   files: ["dist"]
│   scripts:
│     build: "tsx build.ts"
│     prepublishOnly: "pnpm build"
├── tsconfig.json
├── build.ts                                  # Build script (copies + generates metadata)
└── dist/                                     # Build artifact (published to npm)
    ├── .claude-plugin/
    │   └── plugin.json                      # Claude Code plugin manifest
    ├── .cursor-plugin/
    │   └── plugin.json                      # Cursor plugin manifest
    ├── .codex-plugin/
    │   └── plugin.toml                      # Codex plugin manifest
    ├── .gemini-plugin/
    │   └── plugin.json                      # Gemini plugin manifest
    ├── .opencode-plugin/
    │   └── plugin.json                      # OpenCode plugin manifest
    ├── .windsurf-plugin/
    │   └── plugin.json                      # Windsurf plugin manifest
    ├── agents/                               # Copied from research-kit/agents/
    │   ├── rc-experiment.md
    │   ├── rc-ideation.md
    │   ├── rc-literature.md
    │   ├── rc-plan.md
    │   ├── rc-polisher.md
    │   ├── rc-rebuttal.md
    │   ├── rc-reviewer.md
    │   ├── rc-update-spec.md
    │   ├── rc-verify.md
    │   └── rc-writer.md
    ├── skills/                               # Copied from research-kit/skills/
    │   ├── experiment-design/SKILL.md
    │   ├── full-research-workflow/SKILL.md
    │   ├── literature-search/SKILL.md
    │   ├── paper-polish/SKILL.md
    │   ├── sanity-check/SKILL.md
    │   └── submission-sprint/SKILL.md
    └── README.md                             # Plugin documentation
```

### Build Process

`build.ts` responsibilities:
1. **Clean** `dist/` directory
2. **Copy** `research-kit/agents/` → `dist/agents/`
3. **Copy** `research-kit/skills/` → `dist/skills/` (exclude `third_party/`)
4. **Generate** platform metadata files from templates:
   - `.claude-plugin/plugin.json`
   - `.cursor-plugin/plugin.json`
   - `.codex-plugin/plugin.toml`
   - `.gemini-plugin/plugin.json`
   - `.opencode-plugin/plugin.json`
   - `.windsurf-plugin/plugin.json`

---

## 3. Platform Metadata Templates

### Claude Code: `.claude-plugin/plugin.json`

```json
{
  "name": "research-copilot",
  "version": "1.1.13",
  "description": "Academic research workspace: paper writing, review, literature search, and AI Scientist workflow",
  "author": "ldm2060",
  "repository": {
    "type": "git",
    "url": "https://github.com/ldm2060/research_copilot"
  },
  "autoDiscovery": {
    "skills": {
      "enabled": true,
      "paths": ["skills/**/SKILL.md"]
    },
    "agents": {
      "enabled": true,
      "paths": ["agents/*.md"]
    }
  }
}
```

### Cursor: `.cursor-plugin/plugin.json`

Similar structure adapted to Cursor's schema (if documented).

### Codex: `.codex-plugin/plugin.toml`

```toml
[plugin]
name = "research-copilot"
version = "1.1.13"
description = "Academic research workspace: paper writing, review, literature search, and AI Scientist workflow"

[autoDiscovery.skills]
enabled = true
paths = ["skills/**/SKILL.md"]

[autoDiscovery.agents]
enabled = true
paths = ["agents/*.md"]
```

### Other Platforms

Gemini, OpenCode, Windsurf: Adapt to their plugin manifest formats. If a platform lacks documented plugin standards, fallback to auto-discovery via known skill/agent directory conventions.

---

## 4. Integration with `rc init`

### Modified Init Flow

```typescript
// packages/cli/src/commands/init.ts
export function runInit(args: InitArgs): void {
  // 1. Existing: scaffold .research/, copy workflow.md, config.yaml
  // ...existing code...

  // 2. Existing: configure each selected platform
  for (const p of args.platforms) {
    configurePlatform(args.repo, p);
  }

  // 3. NEW: Install @research-copilot/plugin
  installPluginPackage(args.platforms);
}

function installPluginPackage(platforms: string[]): void {
  // Check if @research-copilot/plugin is already installed
  const installed = checkPluginInstalled();
  if (installed) {
    process.stdout.write("@research-copilot/plugin already installed\n");
    return;
  }

  // Install via npm
  process.stdout.write("Installing @research-copilot/plugin...\n");
  execSync("npm install -g @research-copilot/plugin", { stdio: "inherit" });

  // For each platform, link/register the installed plugin
  for (const platform of platforms) {
    registerInstalledPlugin(platform);
  }
}

function registerInstalledPlugin(platform: string): void {
  // Platform-specific plugin registration
  // e.g., for Claude Code: add to ~/.claude/plugins/ or project .claude/settings.json
  // Details depend on each platform's plugin discovery mechanism
}
```

### Platform-Specific Registration

After installing the npm package, `rc init` must register it with each platform:

**Claude Code**:
- Option A: Symlink `~/.npm-global/lib/node_modules/@research-copilot/plugin` → `~/.claude/plugins/research-copilot`
- Option B: Add entry to `~/.claude/plugins.json` pointing to the npm package location
- Option C: Copy plugin contents to project `.claude/` (current approach, but centralized)

**Cursor / Codex / Gemini / OpenCode / Windsurf**:
- Follow each platform's documented plugin installation mechanism
- If undocumented, use auto-discovery conventions (place in expected directories)

---

## 5. User Workflows

### End-User Installation

**Scenario 1: New User**
```bash
# Install CLI globally
npm install -g @research-copilot/cli

# Initialize for Claude Code (auto-installs plugin)
rc init -u username --claude

# Skills are now available
# User can invoke: /full-research-workflow, /literature-search, etc.
```

**Scenario 2: Existing User (Upgrade)**
```bash
# Update CLI
npm update -g @research-copilot/cli

# Re-run init to install plugin (idempotent)
rc init -u username --claude

# Skills now available
```

### Developer Workflow (Dogfooding)

**Local Development**:
```bash
# In research_copilot repo
pnpm install
pnpm build

# Build plugin package
cd packages/plugin
pnpm build

# Link for local testing
npm link

# In another terminal, link the CLI
cd packages/cli
npm link

# Test init with local plugin
rc init -u dev --claude

# Skills should be available from local build
```

**Iteration Loop**:
1. Edit `research-kit/skills/full-research-workflow/SKILL.md`
2. Run `pnpm build` in `packages/plugin/`
3. Plugin is automatically updated (npm link)
4. Test in Claude Code immediately

---

## 6. Build Script Implementation

### `packages/plugin/build.ts`

```typescript
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = path.resolve(__dirname);
const REPO_ROOT = path.resolve(PKG_ROOT, "../..");
const DIST = path.join(PKG_ROOT, "dist");
const RESEARCH_KIT = path.join(REPO_ROOT, "research-kit");

// 1. Clean dist/
if (fs.existsSync(DIST)) {
  fs.rmSync(DIST, { recursive: true });
}
fs.mkdirSync(DIST);

// 2. Copy agents
fs.cpSync(
  path.join(RESEARCH_KIT, "agents"),
  path.join(DIST, "agents"),
  { recursive: true }
);

// 3. Copy skills (exclude third_party)
const skillsSrc = path.join(RESEARCH_KIT, "skills");
const skillsDst = path.join(DIST, "skills");
fs.mkdirSync(skillsDst);
for (const entry of fs.readdirSync(skillsSrc)) {
  if (entry === "third_party") continue;
  const srcPath = path.join(skillsSrc, entry);
  const dstPath = path.join(skillsDst, entry);
  if (fs.statSync(srcPath).isDirectory()) {
    fs.cpSync(srcPath, dstPath, { recursive: true });
  }
}

// 4. Generate platform metadata
generateClaudeCodeManifest();
generateCursorManifest();
generateCodexManifest();
generateGeminiManifest();
generateOpenCodeManifest();
generateWindsurfManifest();

// 5. Copy README
fs.copyFileSync(
  path.join(PKG_ROOT, "README.md"),
  path.join(DIST, "README.md")
);

console.log("✓ Plugin package built successfully");

function generateClaudeCodeManifest(): void {
  const manifest = {
    name: "research-copilot",
    version: getVersion(),
    description: "Academic research workspace: paper writing, review, literature search",
    author: "ldm2060",
    repository: {
      type: "git",
      url: "https://github.com/ldm2060/research_copilot"
    },
    autoDiscovery: {
      skills: {
        enabled: true,
        paths: ["skills/**/SKILL.md"]
      },
      agents: {
        enabled: true,
        paths: ["agents/*.md"]
      }
    }
  };
  const dir = path.join(DIST, ".claude-plugin");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, "plugin.json"),
    JSON.stringify(manifest, null, 2)
  );
}

// ... similar functions for other platforms ...

function getVersion(): string {
  const pkg = JSON.parse(
    fs.readFileSync(path.join(PKG_ROOT, "package.json"), "utf8")
  );
  return pkg.version;
}
```

---

## 7. Version Management

### Synchronized Versioning
- `@research-copilot/cli` and `@research-copilot/plugin` share the same version
- Both packages managed in monorepo with shared version bump
- Release process:
  1. Bump version in root `package.json`
  2. Build all packages: `pnpm -r build`
  3. Publish: `pnpm -r publish` (publishes cli + plugin together)

### Compatibility Check
`rc doctor` should verify plugin version matches CLI:
```typescript
function checkPluginVersion(): { ok: boolean; message: string } {
  const cliVersion = readCliVersion();
  const pluginVersion = readPluginVersion();
  if (cliVersion !== pluginVersion) {
    return {
      ok: false,
      message: `Plugin version mismatch: CLI ${cliVersion}, Plugin ${pluginVersion}. Run: npm update -g @research-copilot/plugin`
    };
  }
  return { ok: true, message: "Plugin version matches CLI" };
}
```

---

## 8. Migration Path

### Phase 1: Create Plugin Package
1. Create `packages/plugin/` directory
2. Implement `build.ts` script
3. Add `package.json` with correct metadata
4. Test local build: `pnpm build`
5. Verify `dist/` structure matches design

### Phase 2: Integrate with Init
1. Modify `packages/cli/src/commands/init.ts` to call `installPluginPackage()`
2. Implement platform-specific registration logic
3. Test on Claude Code first (primary platform)
4. Add idempotency checks (don't reinstall if already present)

### Phase 3: Multi-Platform Testing
1. Test plugin discovery on all 6 platforms
2. Verify skills are callable via slash commands
3. Verify agents are available in agent lists
4. Fix platform-specific issues

### Phase 4: Documentation & Release
1. Update `README.md` with new installation flow
2. Document plugin package in `docs/dev/`
3. Add `rc doctor` plugin version check
4. Publish both packages to npm

### Phase 5: Cleanup
1. Remove old `.claude/skills/sync-submodules` and `validate-plugin-build` (legacy)
2. Update CI to build and publish plugin package
3. Archive old `self/` directory (superseded architecture)

---

## 9. Open Questions & Risks

### Platform Support Matrix

| Platform | Plugin Manifest Format | Auto-Discovery | Registration Method | Status |
|----------|------------------------|----------------|---------------------|---------|
| Claude Code | `.claude-plugin/plugin.json` | ✅ Yes | npm symlink or settings.json | Documented |
| Cursor | `.cursor-plugin/plugin.json` | ❓ Unknown | TBD | Need research |
| Codex | `.codex-plugin/plugin.toml` | ❓ Unknown | TBD | Need research |
| Gemini | `.gemini-plugin/plugin.json` | ❓ Unknown | TBD | Need research |
| OpenCode | `.opencode-plugin/plugin.json` | ❓ Unknown | TBD | Need research |
| Windsurf | `.windsurf-plugin/plugin.json` | ❓ Unknown | TBD | Need research |

**Risk**: If platforms lack documented plugin standards, fallback to manual configuration in `configurePlatform()`.

### Conflict with Existing `.claude/skills/`

Current state: `.claude/skills/` has `sync-submodules` and `validate-plugin-build` (legacy).

**Resolution**:
- Plugin package skills go to a namespaced directory (e.g., `.claude/plugins/research-copilot/skills/`)
- OR: Clear `.claude/skills/` during init and only use plugin-installed skills
- Document expected directory structure

### Local Development vs Published Plugin

**Challenge**: Developers working on research-copilot need to test plugin changes without publishing.

**Solution**: Support both modes in `rc init`:
```bash
# Published plugin (end-user)
rc init -u user --claude

# Local plugin (developer)
rc init -u dev --claude --local-plugin /path/to/research_copilot/packages/plugin/dist
```

---

## 10. Success Criteria

✅ **Functionality**:
- [ ] Users can invoke `/full-research-workflow` and other skills via Claude Code CLI
- [ ] Skills appear in auto-completion suggestions
- [ ] Agents are discoverable in agent lists
- [ ] Works on all 6 target platforms

✅ **Installation**:
- [ ] `npm install -g @research-copilot/cli` + `rc init --claude` installs everything
- [ ] No manual file copying required
- [ ] Idempotent: re-running `rc init` doesn't break existing setup

✅ **Development**:
- [ ] `npm link` workflow allows local plugin testing
- [ ] Changes to `research-kit/skills/` propagate after `pnpm build`
- [ ] Dogfooding works: research-copilot repo can use its own plugin

✅ **Documentation**:
- [ ] README updated with new installation flow
- [ ] Plugin development guide in `docs/dev/`
- [ ] Migration guide for existing users

---

## 11. Alternatives Considered

### Alternative A: Copy Files During Init (Original Approach)

**Description**: `rc init --claude` directly copies `research-kit/skills/` to `.claude/skills/`.

**Pros**:
- Simple implementation
- No npm package complexity

**Cons**:
- ❌ Not cross-platform (each platform needs separate copy logic)
- ❌ No centralized distribution
- ❌ Users must have source repo
- ❌ Skills not independently versioned

**Decision**: Rejected. Does not meet "cross-CLI" and "npm distribution" requirements.

---

### Alternative B: Monolithic CLI with Embedded Skills

**Description**: Bundle skills directly into `@research-copilot/cli` package.

**Pros**:
- Single npm package
- Simpler for users

**Cons**:
- ❌ CLI package becomes bloated (skills are large)
- ❌ Skills can't be installed independently
- ❌ Violates separation of concerns

**Decision**: Rejected. Plugin content should be separate from CLI tooling.

---

## 12. Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Create standalone `@research-copilot/plugin` package | Cleaner separation, independent distribution |
| D2 | Bundle all platform metadata in one package | Simplifies maintenance, users don't pick platforms at install time |
| D3 | Auto-install during `rc init` | Better UX, one command does everything |
| D4 | Support local development via `npm link` | Essential for dogfooding |
| D5 | Sync CLI and plugin versions | Prevents compatibility issues |

---

## 13. Implementation Checklist

**Phase 1: Scaffold**
- [ ] Create `packages/plugin/` directory
- [ ] Add `package.json` with correct metadata
- [ ] Create `build.ts` script skeleton
- [ ] Add to workspace: `pnpm-workspace.yaml`

**Phase 2: Build Script**
- [ ] Implement file copying logic (agents, skills)
- [ ] Generate Claude Code manifest
- [ ] Generate other platform manifests (research needed)
- [ ] Test build: `pnpm build` produces expected `dist/`

**Phase 3: CLI Integration**
- [ ] Modify `init.ts` to install plugin package
- [ ] Implement platform registration for Claude Code
- [ ] Add idempotency checks
- [ ] Test on fresh machine

**Phase 4: Multi-Platform**
- [ ] Research plugin formats for Cursor, Codex, Gemini, OpenCode, Windsurf
- [ ] Implement registration for each platform
- [ ] Test on all platforms (may require VMs/containers)

**Phase 5: Quality & Docs**
- [ ] Add `rc doctor` plugin version check
- [ ] Write `packages/plugin/README.md`
- [ ] Update root `README.md`
- [ ] Add developer guide: `docs/dev/plugin-development.md`
- [ ] Update INSTALLATION.md

**Phase 6: Release**
- [ ] Test full flow on clean environment
- [ ] Publish to npm: `pnpm -r publish`
- [ ] Create GitHub release with changelog
- [ ] Announce to users

---

## Appendix: Platform Research Notes

### Claude Code
- Plugin manifest: `.claude-plugin/plugin.json`
- Auto-discovery paths: `skills/**/SKILL.md`, `agents/*.md`
- Installation: npm package or local directory symlink

### Cursor
- **TODO**: Research plugin format and discovery mechanism

### Codex
- **TODO**: Research plugin format (likely TOML-based)

### Gemini CLI
- **TODO**: Research plugin format

### OpenCode
- **TODO**: Research plugin format

### Windsurf
- **TODO**: Research plugin format
- Note: Agent-less platform, may require workflow/rule adaptation
