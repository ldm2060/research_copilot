#!/usr/bin/env tsx

import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

// Get the directory of this script
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const PLUGIN_ROOT = __dirname;
const PROJECT_ROOT = path.resolve(PLUGIN_ROOT, '../..');
const DIST_DIR = path.join(PLUGIN_ROOT, 'dist');

interface ManifestEntry {
  action: 'add' | 'del';
  sourcePath: string; // relative to PROJECT_ROOT, may contain *
}

/**
 * Parse a manifest file (skill.txt, agent.txt, hook.txt) into entries.
 * Format: each line is "add <path>" or "del <path>"
 */
function parseManifest(filePath: string): ManifestEntry[] {
  const absolutePath = path.join(PROJECT_ROOT, filePath);
  if (!fs.existsSync(absolutePath)) {
    console.warn(`⚠ Manifest file not found: ${filePath}, skipping`);
    return [];
  }

  const content = fs.readFileSync(absolutePath, 'utf-8');
  const entries: ManifestEntry[] = [];

  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const match = trimmed.match(/^(add|del)\s+(.+)$/);
    if (!match) {
      console.warn(`⚠ Skipping invalid line: ${trimmed}`);
      continue;
    }

    entries.push({
      action: match[1] as 'add' | 'del',
      sourcePath: match[2].replace(/\\/g, '/'), // normalize to forward slashes
    });
  }

  return entries;
}

/**
 * Expand a path pattern (may contain *) into actual paths relative to PROJECT_ROOT.
 */
function expandGlob(relPattern: string): string[] {
  const parts = relPattern.split('/');
  const results: string[] = [];

  function walk(currentRel: string, remainingParts: string[]): void {
    if (remainingParts.length === 0) {
      const absPath = path.join(PROJECT_ROOT, currentRel);
      if (fs.existsSync(absPath)) {
        results.push(currentRel);
      }
      return;
    }

    const [nextPart, ...restParts] = remainingParts;
    const absDir = path.join(PROJECT_ROOT, currentRel);

    if (nextPart === '*') {
      // Wildcard: list immediate children
      if (!fs.existsSync(absDir) || !fs.statSync(absDir).isDirectory()) return;
      const children = fs.readdirSync(absDir);
      for (const child of children) {
        const childRel = currentRel ? `${currentRel}/${child}` : child;
        const childAbs = path.join(PROJECT_ROOT, childRel);
        if (fs.statSync(childAbs).isDirectory()) {
          walk(childRel, restParts);
        } else if (restParts.length === 0) {
          results.push(childRel);
        }
      }
    } else {
      const nextRel = currentRel ? `${currentRel}/${nextPart}` : nextPart;
      walk(nextRel, restParts);
    }
  }

  walk('', parts);
  return results;
}

/**
 * Remove and recreate the dist/ directory
 */
function cleanDist(): void {
  console.log('🧹 Cleaning dist directory...');

  if (fs.existsSync(DIST_DIR)) {
    fs.rmSync(DIST_DIR, { recursive: true, force: true });
  }

  fs.mkdirSync(DIST_DIR, { recursive: true });
  console.log('✓ dist/ cleaned and recreated');
}

/**
 * Copy agents based on agent.txt manifest
 */
function copyAgents(): void {
  console.log('📋 Copying agents...');
  const entries = parseManifest('agent.txt');
  const targetDir = path.join(DIST_DIR, 'agents');
  fs.mkdirSync(targetDir, { recursive: true });

  for (const entry of entries) {
    if (entry.action === 'del') {
      console.log(`  ⊘ Skipping (del): ${entry.sourcePath}`);
      continue;
    }

    const expandedPaths = expandGlob(entry.sourcePath);
    for (const relPath of expandedPaths) {
      const absSource = path.join(PROJECT_ROOT, relPath);
      const expanded = expandDirectory(absSource, relPath);
      for (const item of expanded) {
        const targetPath = path.join(DIST_DIR, 'agents', item.relTarget);
        fs.mkdirSync(path.dirname(targetPath), { recursive: true });
        fs.copyFileSync(item.absSource, targetPath);
        console.log(`  ✓ ${item.relTarget}`);
      }
    }
  }

  console.log('✓ Agents copied');
}

/**
 * Copy skills based on skill.txt manifest
 */
function copySkills(): void {
  console.log('🎯 Copying skills...');
  const entries = parseManifest('skill.txt');
  const targetDir = path.join(DIST_DIR, 'skills');
  fs.mkdirSync(targetDir, { recursive: true });

  // Collect paths to delete
  const delPatterns = entries
    .filter(e => e.action === 'del')
    .map(e => e.sourcePath);

  for (const entry of entries) {
    if (entry.action === 'del') {
      console.log(`  ⊘ Excluding (del): ${entry.sourcePath}`);
      continue;
    }

    const expandedPaths = expandGlob(entry.sourcePath);
    for (const relPath of expandedPaths) {
      const absSource = path.join(PROJECT_ROOT, relPath);

      // For self/skills (no wildcard at end), copy the whole directory
      if (!entry.sourcePath.endsWith('*') && fs.statSync(absSource).isDirectory()) {
        // Copy all subdirectories (each skill is a directory)
        const subdirs = fs.readdirSync(absSource).filter(name => {
          const subAbs = path.join(absSource, name);
          if (!fs.statSync(subAbs).isDirectory()) return false;
          // Check del patterns
          return !isDelMatch(name, delPatterns);
        });

        for (const sub of subdirs) {
          const subAbs = path.join(absSource, sub);
          const expanded = expandDirectory(subAbs, `${relPath}/${sub}`);
          for (const item of expanded) {
            // Check del patterns against relative path
            if (isDelMatchPath(item.relTarget, delPatterns)) {
              console.log(`  ⊘ Excluded by del: ${item.relTarget}`);
              continue;
            }
            const targetPath = path.join(DIST_DIR, 'skills', item.relTarget);
            fs.mkdirSync(path.dirname(targetPath), { recursive: true });
            fs.copyFileSync(item.absSource, targetPath);
            console.log(`  ✓ ${item.relTarget}`);
          }
        }
      } else {
        // Wildcard or file path
        const expanded = expandDirectory(absSource, relPath);
        for (const item of expanded) {
          if (isDelMatchPath(item.relTarget, delPatterns)) {
            console.log(`  ⊘ Excluded by del: ${item.relTarget}`);
            continue;
          }
          const targetPath = path.join(DIST_DIR, 'skills', item.relTarget);
          fs.mkdirSync(path.dirname(targetPath), { recursive: true });
          fs.copyFileSync(item.absSource, targetPath);
          console.log(`  ✓ ${item.relTarget}`);
        }
      }
    }
  }

  console.log('✓ Skills copied');
}

/**
 * Copy hooks based on hook.txt manifest
 */
function copyHooks(): void {
  console.log('🪝 Copying hooks...');
  const entries = parseManifest('hook.txt');

  for (const entry of entries) {
    if (entry.action === 'del') {
      console.log(`  ⊘ Skipping (del): ${entry.sourcePath}`);
      continue;
    }

    const expandedPaths = expandGlob(entry.sourcePath);
    for (const relPath of expandedPaths) {
      const absSource = path.join(PROJECT_ROOT, relPath);
      const expanded = expandDirectory(absSource, relPath);
      for (const item of expanded) {
        const targetPath = path.join(DIST_DIR, 'hooks', item.relTarget);
        fs.mkdirSync(path.dirname(targetPath), { recursive: true });
        fs.copyFileSync(item.absSource, targetPath);
        console.log(`  ✓ hooks/${item.relTarget}`);
      }
    }
  }

  console.log('✓ Hooks copied');
}

/**
 * Copy README.md to dist/
 */
function copyReadme(): void {
  console.log('📄 Copying README...');

  // Prefer research-kit README, fallback to project README
  const candidates = [
    path.join(PROJECT_ROOT, 'research-kit', 'README.md'),
    path.join(PROJECT_ROOT, 'README.md'),
  ];

  for (const sourceFile of candidates) {
    if (fs.existsSync(sourceFile)) {
      fs.copyFileSync(sourceFile, path.join(DIST_DIR, 'README.md'));
      console.log(`✓ Copied README.md from ${sourceFile}`);
      return;
    }
  }

  console.warn('⚠ No README.md found');
}

/**
 * Expand a directory recursively into {absSource, relTarget} pairs.
 * relTarget is relative to the top-level skill/agent/hook directory.
 */
function expandDirectory(
  absDir: string,
  manifestRelPath: string
): Array<{ absSource: string; relTarget: string }> {
  const results: Array<{ absSource: string; relTarget: string }> = [];

  if (!fs.existsSync(absDir)) {
    console.warn(`  ⚠ Source not found: ${absDir}`);
    return results;
  }

  if (!fs.statSync(absDir).isDirectory()) {
    // Single file
    const fileName = path.basename(absDir);
    return [{ absSource: absDir, relTarget: fileName }];
  }

  // Determine the "name" for this directory in dist
  // e.g. "self/skills/arxivsub-skill" -> "arxivsub-skill"
  // e.g. "third_party/humanizer" -> "humanizer"
  const pathParts = manifestRelPath.split('/');
  const dirName = pathParts[pathParts.length - 1];

  function walk(dir: string, relPrefix: string): void {
    const items = fs.readdirSync(dir);
    for (const item of items) {
      // Skip __pycache__ and .pyc files
      if (item === '__pycache__' || item.endsWith('.pyc')) continue;

      const absPath = path.join(dir, item);
      const rel = relPrefix ? `${relPrefix}/${item}` : item;
      if (fs.statSync(absPath).isDirectory()) {
        walk(absPath, rel);
      } else {
        results.push({ absSource: absPath, relTarget: rel });
      }
    }
  }

  walk(absDir, dirName);
  return results;
}

/**
 * Check if a directory/file name matches any del pattern.
 */
function isDelMatch(name: string, delPatterns: string[]): boolean {
  return delPatterns.some(pattern => {
    const lastPart = pattern.split('/').pop()!;
    return name === lastPart || name === pattern;
  });
}

/**
 * Check if a relative target path matches any del pattern.
 */
function isDelMatchPath(relTarget: string, delPatterns: string[]): boolean {
  return delPatterns.some(pattern => {
    // Match if the pattern appears as a segment in the path
    return relTarget.includes(pattern) ||
      relTarget.startsWith(pattern + '/') ||
      relTarget.split('/').some(seg => seg === pattern);
  });
}

/**
 * Read version from package.json
 */
function getVersion(): string {
  const packageJsonPath = path.join(PLUGIN_ROOT, 'package.json');
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
  return packageJson.version;
}

/**
 * Generate platform.json metadata
 */
function generatePlatformMetadata(): void {
  console.log('🔧 Generating platform metadata...');

  generateClaudeCodeManifest();
  generateCursorManifest();
  generateCodexManifest();
  generateGeminiManifest();
  generateOpenCodeManifest();
  generateWindsurfManifest();

  console.log('✓ Generated platform metadata for all 6 platforms');
}

function generateClaudeCodeManifest(): void {
  const version = getVersion();
  const targetDir = path.join(DIST_DIR, '.claude-plugin');
  const targetFile = path.join(targetDir, 'plugin.json');
  fs.mkdirSync(targetDir, { recursive: true });

  const manifest = {
    name: 'research-copilot',
    version,
    description: 'AI research automation skills and agents',
    author: 'ldm2060',
    homepage: 'https://github.com/ldm2060/research_copilot',
    autoDiscovery: {
      agents: 'agents/**/*.md',
      skills: 'skills/**/*.md',
      hooks: 'hooks/**/*.json',
    },
  };

  fs.writeFileSync(targetFile, JSON.stringify(manifest, null, 2));
  console.log(`  ✓ Claude Code: ${targetFile}`);
}

function generateCursorManifest(): void {
  const version = getVersion();
  const targetDir = path.join(DIST_DIR, '.cursor-plugin');
  const targetFile = path.join(targetDir, 'plugin.json');
  fs.mkdirSync(targetDir, { recursive: true });

  const manifest = {
    name: 'research-copilot',
    version,
    description: 'AI research automation skills and agents',
    author: 'ldm2060',
    homepage: 'https://github.com/ldm2060/research_copilot',
    agents: 'agents/**/*.md',
    skills: 'skills/**/*.md',
    hooks: 'hooks/**/*.json',
  };

  fs.writeFileSync(targetFile, JSON.stringify(manifest, null, 2));
  console.log(`  ✓ Cursor: ${targetFile}`);
}

function generateCodexManifest(): void {
  const version = getVersion();
  const targetDir = path.join(DIST_DIR, '.codex-plugin');
  const targetFile = path.join(targetDir, 'plugin.toml');
  fs.mkdirSync(targetDir, { recursive: true });

  const toml = `name = "research-copilot"
version = "${version}"
description = "AI research automation skills and agents"
author = "ldm2060"
homepage = "https://github.com/ldm2060/research_copilot"

[discovery]
agents = "agents/**/*.md"
skills = "skills/**/*.md"
hooks = "hooks/**/*.json"
`;

  fs.writeFileSync(targetFile, toml);
  console.log(`  ✓ Codex: ${targetFile}`);
}

function generateGeminiManifest(): void {
  const version = getVersion();
  const targetDir = path.join(DIST_DIR, '.gemini-plugin');
  const targetFile = path.join(targetDir, 'plugin.json');
  fs.mkdirSync(targetDir, { recursive: true });

  const manifest = {
    name: 'research-copilot',
    version,
    description: 'AI research automation skills and agents',
    author: 'ldm2060',
    homepage: 'https://github.com/ldm2060/research_copilot',
    components: {
      agents: 'agents/**/*.md',
      skills: 'skills/**/*.md',
      hooks: 'hooks/**/*.json',
    },
  };

  fs.writeFileSync(targetFile, JSON.stringify(manifest, null, 2));
  console.log(`  ✓ Gemini: ${targetFile}`);
}

function generateOpenCodeManifest(): void {
  const version = getVersion();
  const targetDir = path.join(DIST_DIR, '.opencode-plugin');
  const targetFile = path.join(targetDir, 'plugin.json');
  fs.mkdirSync(targetDir, { recursive: true });

  const manifest = {
    name: 'research-copilot',
    version,
    description: 'AI research automation skills and agents',
    author: 'ldm2060',
    homepage: 'https://github.com/ldm2060/research_copilot',
    patterns: {
      agents: 'agents/**/*.md',
      skills: 'skills/**/*.md',
      hooks: 'hooks/**/*.json',
    },
  };

  fs.writeFileSync(targetFile, JSON.stringify(manifest, null, 2));
  console.log(`  ✓ OpenCode: ${targetFile}`);
}

function generateWindsurfManifest(): void {
  const version = getVersion();
  const targetDir = path.join(DIST_DIR, '.windsurf-plugin');
  const targetFile = path.join(targetDir, 'plugin.json');
  fs.mkdirSync(targetDir, { recursive: true });

  const manifest = {
    name: 'research-copilot',
    version,
    description: 'AI research automation skills and agents',
    author: 'ldm2060',
    homepage: 'https://github.com/ldm2060/research_copilot',
    autoload: {
      agents: 'agents/**/*.md',
      skills: 'skills/**/*.md',
      hooks: 'hooks/**/*.json',
    },
  };

  fs.writeFileSync(targetFile, JSON.stringify(manifest, null, 2));
  console.log(`  ✓ Windsurf: ${targetFile}`);
}

/**
 * Main build function
 */
async function main(): Promise<void> {
  console.log('🚀 Starting @research-copilot/plugin build...\n');
  console.log(`   Project root: ${PROJECT_ROOT}`);
  console.log(`   Dist dir:     ${DIST_DIR}\n`);

  try {
    // Step 1: Clean dist directory
    cleanDist();

    // Step 2: Copy agents (from agent.txt)
    copyAgents();

    // Step 3: Copy skills (from skill.txt)
    copySkills();

    // Step 4: Copy hooks (from hook.txt)
    copyHooks();

    // Step 5: Copy README
    copyReadme();

    // Step 6: Generate platform metadata
    generatePlatformMetadata();

    // Summary
    console.log('\n📊 Build summary:');
    for (const subdir of ['agents', 'skills', 'hooks']) {
      const dir = path.join(DIST_DIR, subdir);
      if (fs.existsSync(dir)) {
        const files = countFiles(dir);
        console.log(`   ${subdir}: ${files} files`);
      }
    }

    console.log('\n✅ Build completed successfully!');
  } catch (error) {
    console.error('\n❌ Build failed:', error);
    process.exit(1);
  }
}

/**
 * Count files recursively in a directory
 */
function countFiles(dir: string): number {
  let count = 0;
  const items = fs.readdirSync(dir);
  for (const item of items) {
    const itemPath = path.join(dir, item);
    if (fs.statSync(itemPath).isDirectory()) {
      count += countFiles(itemPath);
    } else {
      count++;
    }
  }
  return count;
}

// Run the build
main();
