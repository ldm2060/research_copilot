# @research-copilot/plugin Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `@research-copilot/plugin` npm package that bundles research-kit skills/agents with multi-platform metadata for auto-discovery across CLI platforms.

**Architecture:** Standalone npm package with build script that copies research-kit content and generates platform-specific plugin manifests (Claude Code, Cursor, Codex, Gemini, OpenCode, Windsurf). Auto-installs during `rc init`.

**Tech Stack:** TypeScript, tsup, Node.js fs/path, pnpm workspaces

---

## File Structure

**New files:**
- `packages/plugin/package.json` - Plugin package manifest
- `packages/plugin/tsconfig.json` - TypeScript config
- `packages/plugin/build.ts` - Build script (copy + generate metadata)
- `packages/plugin/README.md` - Plugin documentation
- `packages/plugin/.gitignore` - Ignore dist/

**Modified files:**
- `packages/cli/src/commands/init.ts` - Add plugin installation
- `packages/cli/src/commands/doctor.ts` - Add plugin version check
- Root `README.md` - Update installation instructions

**Generated at build time (in dist/):**
- `dist/.claude-plugin/plugin.json`
- `dist/.cursor-plugin/plugin.json`
- `dist/.codex-plugin/plugin.toml`
- `dist/.gemini-plugin/plugin.json`
- `dist/.opencode-plugin/plugin.json`
- `dist/.windsurf-plugin/plugin.json`
- `dist/agents/` (10 files)
- `dist/skills/` (6 directories)
- `dist/README.md`

---

## Task 1: Scaffold Plugin Package

**Files:**
- Create: `packages/plugin/package.json`
- Create: `packages/plugin/tsconfig.json`
- Create: `packages/plugin/.gitignore`
- Create: `packages/plugin/README.md`


- [ ] **Step 1: Create package.json**

```json
{
  "name": "@research-copilot/plugin",
  "version": "1.1.13",
  "description": "Research Copilot plugin for multiple CLI platforms",
  "type": "module",
  "files": ["dist"],
  "keywords": ["research", "copilot", "ai", "plugin", "claude", "cursor"],
  "author": "ldm2060",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/ldm2060/research_copilot.git",
    "directory": "packages/plugin"
  },
  "engines": {
    "node": ">=18.0.0"
  },
  "scripts": {
    "build": "tsx build.ts",
    "prepublishOnly": "pnpm build"
  },
  "devDependencies": {
    "tsx": "^4.19.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "."
  },
  "include": ["build.ts"]
}
```

- [ ] **Step 3: Create .gitignore**

```
dist/
node_modules/
*.log
```


- [ ] **Step 4: Create README.md**

```markdown
# @research-copilot/plugin

Research Copilot plugin for multiple CLI platforms (Claude Code, Cursor, Codex, Gemini, OpenCode, Windsurf).

## Installation

This package is automatically installed when you run:

\`\`\`bash
rc init -u username --claude
\`\`\`

For manual installation:

\`\`\`bash
npm install -g @research-copilot/plugin
\`\`\`

## Contents

- 6 orchestration skills for research workflows
- 10 research agents (rc-literature, rc-writer, etc.)
- Multi-platform plugin metadata for auto-discovery

## Skills

- `/full-research-workflow` - Complete pipeline (literature → submission)
- `/literature-search` - Focused paper search + baseline locking
- `/experiment-design` - Design and launch experiments
- `/paper-polish` - De-AI and style refinement
- `/submission-sprint` - Iterative review-fix loop
- `/sanity-check` - 6-dimension final audit
```

- [ ] **Step 5: Verify package structure**

Run: `ls -la packages/plugin/`
Expected: package.json, tsconfig.json, .gitignore, README.md

- [ ] **Step 6: Commit**

```bash
git add packages/plugin/
git commit -m "feat(plugin): scaffold @research-copilot/plugin package

Add package.json, tsconfig, gitignore, and README for new plugin package"
```

---

## Task 2: Build Script - Core Logic

**Files:**
- Create: `packages/plugin/build.ts`


- [ ] **Step 1: Write build script skeleton**

```typescript
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = path.resolve(__dirname);
const REPO_ROOT = path.resolve(PKG_ROOT, "../..");
const DIST = path.join(PKG_ROOT, "dist");
const RESEARCH_KIT = path.join(REPO_ROOT, "research-kit");

function main(): void {
  console.log("Building @research-copilot/plugin...");
  
  // 1. Clean dist/
  cleanDist();
  
  // 2. Copy agents
  copyAgents();
  
  // 3. Copy skills
  copySkills();
  
  // 4. Generate platform metadata
  generatePlatformMetadata();
  
  // 5. Copy README
  copyReadme();
  
  console.log("✓ Plugin package built successfully");
}

main();
```

- [ ] **Step 2: Implement cleanDist()**

```typescript
function cleanDist(): void {
  if (fs.existsSync(DIST)) {
    fs.rmSync(DIST, { recursive: true, force: true });
  }
  fs.mkdirSync(DIST, { recursive: true });
  console.log("  ✓ Cleaned dist/");
}
```


- [ ] **Step 3: Implement copyAgents()**

```typescript
function copyAgents(): void {
  const agentsSrc = path.join(RESEARCH_KIT, "agents");
  const agentsDst = path.join(DIST, "agents");
  fs.cpSync(agentsSrc, agentsDst, { recursive: true });
  const count = fs.readdirSync(agentsDst).filter(f => f.endsWith(".md")).length;
  console.log(`  ✓ Copied ${count} agents`);
}
```

- [ ] **Step 4: Implement copySkills()**

```typescript
function copySkills(): void {
  const skillsSrc = path.join(RESEARCH_KIT, "skills");
  const skillsDst = path.join(DIST, "skills");
  fs.mkdirSync(skillsDst, { recursive: true });
  
  let count = 0;
  for (const entry of fs.readdirSync(skillsSrc)) {
    if (entry === "third_party") continue;
    const srcPath = path.join(skillsSrc, entry);
    if (!fs.statSync(srcPath).isDirectory()) continue;
    
    const dstPath = path.join(skillsDst, entry);
    fs.cpSync(srcPath, dstPath, { recursive: true });
    count++;
  }
  console.log(`  ✓ Copied ${count} skills`);
}
```

- [ ] **Step 5: Implement copyReadme()**

```typescript
function copyReadme(): void {
  fs.copyFileSync(
    path.join(PKG_ROOT, "README.md"),
    path.join(DIST, "README.md")
  );
  console.log("  ✓ Copied README");
}
```


- [ ] **Step 6: Test build script**

Run: `cd packages/plugin && pnpm build`
Expected: Console output showing "✓ Plugin package built successfully", dist/ directory created with agents/ and skills/

- [ ] **Step 7: Verify copied content**

Run: `ls -la packages/plugin/dist/`
Expected: agents/, skills/, README.md

Run: `ls packages/plugin/dist/agents/`
Expected: 10 .md files (rc-experiment.md, rc-ideation.md, etc.)

Run: `ls packages/plugin/dist/skills/`
Expected: 6 directories (experiment-design, full-research-workflow, literature-search, paper-polish, sanity-check, submission-sprint)

- [ ] **Step 8: Commit**

```bash
git add packages/plugin/build.ts
git commit -m "feat(plugin): add build script core logic

Implement cleanDist, copyAgents, copySkills, copyReadme functions"
```

---

## Task 3: Build Script - Platform Metadata Generation

**Files:**
- Modify: `packages/plugin/build.ts`

- [ ] **Step 1: Add getVersion() helper**

```typescript
function getVersion(): string {
  const pkg = JSON.parse(
    fs.readFileSync(path.join(PKG_ROOT, "package.json"), "utf8")
  );
  return pkg.version;
}
```


- [ ] **Step 2: Implement generatePlatformMetadata()**

```typescript
function generatePlatformMetadata(): void {
  generateClaudeCodeManifest();
  generateCursorManifest();
  generateCodexManifest();
  generateGeminiManifest();
  generateOpenCodeManifest();
  generateWindsurfManifest();
  console.log("  ✓ Generated 6 platform manifests");
}
```

- [ ] **Step 3: Implement generateClaudeCodeManifest()**

```typescript
function generateClaudeCodeManifest(): void {
  const manifest = {
    name: "research-copilot",
    version: getVersion(),
    description: "Academic research workspace: paper writing, review, literature search, and AI Scientist workflow",
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
    JSON.stringify(manifest, null, 2) + "\n"
  );
}
```


- [ ] **Step 4: Implement other platform manifest generators (stub for now)**

```typescript
function generateCursorManifest(): void {
  // Similar to Claude Code - JSON format
  const manifest = {
    name: "research-copilot",
    version: getVersion(),
    description: "Academic research workspace: paper writing, review, literature search",
    autoDiscovery: {
      skills: { enabled: true, paths: ["skills/**/SKILL.md"] },
      agents: { enabled: true, paths: ["agents/*.md"] }
    }
  };
  const dir = path.join(DIST, ".cursor-plugin");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "plugin.json"), JSON.stringify(manifest, null, 2) + "\n");
}

function generateCodexManifest(): void {
  // TOML format
  const toml = `[plugin]
name = "research-copilot"
version = "${getVersion()}"
description = "Academic research workspace: paper writing, review, literature search"

[autoDiscovery.skills]
enabled = true
paths = ["skills/**/SKILL.md"]

[autoDiscovery.agents]
enabled = true
paths = ["agents/*.md"]
`;
  const dir = path.join(DIST, ".codex-plugin");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "plugin.toml"), toml);
}

function generateGeminiManifest(): void {
  const manifest = {
    name: "research-copilot",
    version: getVersion(),
    description: "Academic research workspace",
    autoDiscovery: {
      skills: { enabled: true, paths: ["skills/**/SKILL.md"] },
      agents: { enabled: true, paths: ["agents/*.md"] }
    }
  };
  const dir = path.join(DIST, ".gemini-plugin");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "plugin.json"), JSON.stringify(manifest, null, 2) + "\n");
}


function generateOpenCodeManifest(): void {
  const manifest = {
    name: "research-copilot",
    version: getVersion(),
    description: "Academic research workspace",
    autoDiscovery: {
      skills: { enabled: true, paths: ["skills/**/SKILL.md"] },
      agents: { enabled: true, paths: ["agents/*.md"] }
    }
  };
  const dir = path.join(DIST, ".opencode-plugin");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "plugin.json"), JSON.stringify(manifest, null, 2) + "\n");
}

function generateWindsurfManifest(): void {
  const manifest = {
    name: "research-copilot",
    version: getVersion(),
    description: "Academic research workspace",
    autoDiscovery: {
      skills: { enabled: true, paths: ["skills/**/SKILL.md"] },
      agents: { enabled: true, paths: ["agents/*.md"] }
    }
  };
  const dir = path.join(DIST, ".windsurf-plugin");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "plugin.json"), JSON.stringify(manifest, null, 2) + "\n");
}
```

- [ ] **Step 5: Test build with metadata generation**

Run: `cd packages/plugin && pnpm build`
Expected: Console shows "✓ Generated 6 platform manifests"

- [ ] **Step 6: Verify manifests**

Run: `find packages/plugin/dist/ -name "plugin.*" -o -name "*.toml"`
Expected: 6 files (.claude-plugin/plugin.json, .cursor-plugin/plugin.json, .codex-plugin/plugin.toml, .gemini-plugin/plugin.json, .opencode-plugin/plugin.json, .windsurf-plugin/plugin.json)

Run: `cat packages/plugin/dist/.claude-plugin/plugin.json`
Expected: Valid JSON with autoDiscovery paths


- [ ] **Step 7: Commit**

```bash
git add packages/plugin/build.ts
git commit -m "feat(plugin): add platform metadata generation

Generate plugin manifests for all 6 platforms (Claude Code, Cursor, Codex, Gemini, OpenCode, Windsurf)"
```

---

## Task 4: CLI Integration - Plugin Installation

**Files:**
- Modify: `packages/cli/src/commands/init.ts`
- Modify: `packages/cli/package.json` (add child_process import if needed)

- [ ] **Step 1: Add plugin installation function to init.ts**

```typescript
import { execSync } from "node:child_process";

function installPluginPackage(platforms: string[]): void {
  // Check if plugin is already installed globally
  try {
    execSync("npm list -g @research-copilot/plugin", { stdio: "pipe" });
    process.stdout.write("@research-copilot/plugin already installed\n");
    return;
  } catch {
    // Not installed, proceed
  }
  
  // Install plugin
  process.stdout.write("Installing @research-copilot/plugin...\n");
  try {
    execSync("npm install -g @research-copilot/plugin", { stdio: "inherit" });
    process.stdout.write("✓ Plugin installed\n");
  } catch (err) {
    process.stderr.write("Warning: Failed to install plugin globally. You may need to run: npm install -g @research-copilot/plugin\n");
  }
}
```


- [ ] **Step 2: Call installPluginPackage in runInit**

```typescript
export function runInit(args: InitArgs): void {
  const p = researchPaths(args.repo);
  for (const d of [p.tasks, p.spec, p.workspace, p.runtime]) fs.mkdirSync(d, { recursive: true });
  for (const s of ["venue", "writing", "baselines", "methodology", "novelty"])
    fs.mkdirSync(path.join(p.spec, s), { recursive: true });
  const KIT = kitRoot(__dirname);
  fs.copyFileSync(path.join(KIT, "workflow.md"), p.workflow);
  fs.copyFileSync(path.join(KIT, "config.defaults.yaml"), p.config);
  
  // Configure platforms
  for (const platform of args.platforms) configurePlatform(args.repo, platform);
  
  // NEW: Install plugin package
  installPluginPackage(args.platforms);
}
```

- [ ] **Step 3: Test init with plugin installation (manual for now)**

Note: Full test requires published package. For now, verify code compiles.

Run: `cd packages/cli && pnpm build`
Expected: No TypeScript errors

- [ ] **Step 4: Commit**

```bash
git add packages/cli/src/commands/init.ts
git commit -m "feat(cli): add plugin package auto-installation to init

rc init now installs @research-copilot/plugin globally"
```

---

## Task 5: CLI Integration - Version Check in Doctor

**Files:**
- Modify: `packages/cli/src/commands/doctor.ts`


- [ ] **Step 1: Add plugin version check function**

```typescript
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

function checkPluginVersion(): { ok: boolean; message: string } {
  // Get CLI version
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const pkgPath = join(__dirname, "..", "package.json");
  const cliVersion = JSON.parse(readFileSync(pkgPath, "utf8")).version;
  
  // Get plugin version
  let pluginVersion: string;
  try {
    const output = execSync("npm list -g @research-copilot/plugin --json", { encoding: "utf8" });
    const data = JSON.parse(output);
    pluginVersion = data.dependencies?.["@research-copilot/plugin"]?.version;
    
    if (!pluginVersion) {
      return {
        ok: false,
        message: "Plugin not installed. Run: npm install -g @research-copilot/plugin"
      };
    }
  } catch {
    return {
      ok: false,
      message: "Plugin not installed. Run: npm install -g @research-copilot/plugin"
    };
  }
  
  // Compare versions
  if (cliVersion !== pluginVersion) {
    return {
      ok: false,
      message: `Plugin version mismatch: CLI ${cliVersion}, Plugin ${pluginVersion}. Run: npm update -g @research-copilot/plugin`
    };
  }
  
  return { ok: true, message: `Plugin version ${pluginVersion} matches CLI` };
}
```


- [ ] **Step 2: Integrate into runDoctor**

```typescript
export function runDoctor(repo: string): { ok: boolean; report: string[] } {
  const report: string[] = [];
  let allOk = true;
  
  // Existing checks
  const p = researchPaths(repo);
  if (fs.existsSync(p.root)) {
    report.push("OK  .research/ exists");
  } else {
    report.push("FAIL .research/ exists");
    allOk = false;
  }
  
  if (fs.existsSync(p.workflow)) {
    report.push("OK  workflow.md exists");
  } else {
    report.push("FAIL workflow.md exists");
    allOk = false;
  }
  
  const settingsPath = path.join(repo, ".claude/settings.json");
  if (fs.existsSync(settingsPath)) {
    report.push("OK  .claude/settings.json exists");
  } else {
    report.push("FAIL .claude/settings.json exists");
    allOk = false;
  }
  
  // NEW: Plugin version check
  const pluginCheck = checkPluginVersion();
  if (pluginCheck.ok) {
    report.push(`OK  ${pluginCheck.message}`);
  } else {
    report.push(`WARN ${pluginCheck.message}`);
    // Don't set allOk = false for plugin warnings (non-critical)
  }
  
  return { ok: allOk, report };
}
```

- [ ] **Step 3: Test doctor command**

Run: `node packages/cli/dist/rc.js doctor`
Expected: Output includes plugin version check (WARN if not installed, OK if matches)

- [ ] **Step 4: Commit**

```bash
git add packages/cli/src/commands/doctor.ts
git commit -m "feat(cli): add plugin version check to doctor command

rc doctor now verifies plugin version matches CLI"
```

---

## Task 6: Documentation Updates

**Files:**
- Modify: Root `README.md`


- [ ] **Step 1: Update Installation section in README**

Find the section starting with "## Installation" and update the Quick Start:

```markdown
### Quick Start (npx - no installation)

\`\`\`bash
npx @research-copilot/cli init --user your-name --claude
\`\`\`

This automatically installs both the CLI and the plugin package.
```

- [ ] **Step 2: Add note about plugin package**

After the installation methods, add:

```markdown
**Note:** The `rc init` command automatically installs `@research-copilot/plugin`, which provides 6 research workflow skills and 10 agents for Claude Code and other supported platforms.
```

- [ ] **Step 3: Verify README renders correctly**

Run: `cat README.md | grep -A 5 "Quick Start"`
Expected: Updated text about automatic plugin installation

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update README with plugin package information

Clarify that rc init auto-installs plugin package"
```

---

## Task 7: Local Development Setup

**Files:**
- Modify: `packages/plugin/package.json` (add dev script)
- Create: `packages/plugin/.npmignore`

- [ ] **Step 1: Add link script to package.json**

```json
{
  "scripts": {
    "build": "tsx build.ts",
    "prepublishOnly": "pnpm build",
    "dev": "pnpm build && npm link"
  }
}
```


- [ ] **Step 2: Create .npmignore**

```
build.ts
tsconfig.json
.gitignore
*.log
node_modules/
```

- [ ] **Step 3: Test local development workflow**

Run: `cd packages/plugin && pnpm dev`
Expected: Build succeeds, npm link creates symlink

Run: `npm list -g @research-copilot/plugin`
Expected: Shows linked package

- [ ] **Step 4: Commit**

```bash
git add packages/plugin/package.json packages/plugin/.npmignore
git commit -m "feat(plugin): add local development support

Add dev script for npm link workflow and npmignore"
```

---

## Task 8: Final Testing & Validation

**Files:**
- None (testing only)

- [ ] **Step 1: Clean build test**

```bash
# Clean everything
rm -rf packages/plugin/dist packages/plugin/node_modules
cd packages/plugin
pnpm install
pnpm build
```

Expected: dist/ created with all files

- [ ] **Step 2: Verify dist structure**

Run: `tree packages/plugin/dist/ -L 2` (or `find packages/plugin/dist/ -type f | head -20`)
Expected:
- .claude-plugin/plugin.json
- .cursor-plugin/plugin.json
- .codex-plugin/plugin.toml
- .gemini-plugin/plugin.json
- .opencode-plugin/plugin.json
- .windsurf-plugin/plugin.json
- agents/*.md (10 files)
- skills/*/ (6 directories with SKILL.md)
- README.md


- [ ] **Step 3: Test CLI integration**

```bash
# Build CLI
cd packages/cli
pnpm build

# Test doctor (should warn plugin not installed)
node dist/rc.js doctor
```

Expected: "WARN Plugin not installed" message

- [ ] **Step 4: Test with linked plugin**

```bash
# Link plugin locally
cd packages/plugin
pnpm dev

# Run doctor again
cd ../cli
node dist/rc.js doctor
```

Expected: "OK Plugin version 1.1.13 matches CLI"

- [ ] **Step 5: Verify package is publishable**

Run: `cd packages/plugin && npm pack --dry-run`
Expected: Shows files that would be included (only dist/ and package.json)

---

## Implementation Complete

All tasks are complete. The plugin package is ready for:

1. **Local testing**: `cd packages/plugin && pnpm dev`
2. **Publishing**: `cd packages/plugin && npm publish` (requires npm authentication)
3. **Integration**: `rc init --claude` will auto-install the plugin

**Next Steps for Production:**
- Publish `@research-copilot/plugin` to npm
- Test end-to-end: fresh install → `npm install -g @research-copilot/cli` → `rc init --claude` → verify skills appear
- Update CI/CD to build and publish both packages together

---

## Self-Review Checklist

✅ **Spec coverage**: All sections implemented
- Package structure: ✓ (Task 1)
- Build script: ✓ (Tasks 2-3)
- Platform metadata: ✓ (Task 3)
- CLI integration: ✓ (Tasks 4-5)
- Documentation: ✓ (Task 6)
- Local dev: ✓ (Task 7)

✅ **No placeholders**: All code blocks are complete

✅ **Type consistency**: Function names and signatures match across tasks

✅ **Testing**: Each task includes verification steps

