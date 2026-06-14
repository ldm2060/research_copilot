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
const RESEARCH_KIT_DIR = path.join(PROJECT_ROOT, 'research-kit');
const DIST_DIR = path.join(PLUGIN_ROOT, 'dist');

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
 * Copy research-kit/agents/ to dist/agents/
 */
function copyAgents(): void {
  console.log('📋 Copying agents...');

  const sourceDir = path.join(RESEARCH_KIT_DIR, 'agents');
  const targetDir = path.join(DIST_DIR, 'agents');

  if (!fs.existsSync(sourceDir)) {
    console.error(`❌ Source directory not found: ${sourceDir}`);
    process.exit(1);
  }

  copyDirectory(sourceDir, targetDir);
  console.log(`✓ Copied agents from ${sourceDir} to ${targetDir}`);
}

/**
 * Copy research-kit/skills/ to dist/skills/, excluding third_party
 */
function copySkills(): void {
  console.log('🎯 Copying skills...');

  const sourceDir = path.join(RESEARCH_KIT_DIR, 'skills');
  const targetDir = path.join(DIST_DIR, 'skills');

  if (!fs.existsSync(sourceDir)) {
    console.error(`❌ Source directory not found: ${sourceDir}`);
    process.exit(1);
  }

  copyDirectory(sourceDir, targetDir, (itemPath) => {
    // Skip third_party directory
    const relativePath = path.relative(sourceDir, itemPath);
    if (relativePath.startsWith('third_party')) {
      console.log(`⊘ Skipping: ${relativePath}`);
      return false;
    }
    return true;
  });

  console.log(`✓ Copied skills from ${sourceDir} to ${targetDir} (excluding third_party)`);
}

/**
 * Copy README.md to dist/
 */
function copyReadme(): void {
  console.log('📄 Copying README...');

  const sourceFile = path.join(RESEARCH_KIT_DIR, 'README.md');
  const targetFile = path.join(DIST_DIR, 'README.md');

  if (!fs.existsSync(sourceFile)) {
    console.error(`❌ README.md not found: ${sourceFile}`);
    process.exit(1);
  }

  fs.copyFileSync(sourceFile, targetFile);
  console.log(`✓ Copied README.md to ${targetFile}`);
}

/**
 * Generate platform.json metadata
 * (Implementation pending - Task 3)
 */
function generatePlatformMetadata(): void {
  console.log('🔧 Generating platform metadata...');
  // TODO: Implement in Task 3
  console.log('⚠ Platform metadata generation pending (Task 3)');
}

/**
 * Recursively copy a directory with optional filter
 */
function copyDirectory(
  source: string,
  target: string,
  filter?: (itemPath: string) => boolean
): void {
  // Create target directory
  fs.mkdirSync(target, { recursive: true });

  // Read source directory
  const items = fs.readdirSync(source);

  for (const item of items) {
    const sourcePath = path.join(source, item);
    const targetPath = path.join(target, item);

    // Apply filter if provided
    if (filter && !filter(sourcePath)) {
      continue;
    }

    const stats = fs.statSync(sourcePath);

    if (stats.isDirectory()) {
      // Recursively copy subdirectory
      copyDirectory(sourcePath, targetPath, filter);
    } else if (stats.isFile()) {
      // Copy file
      fs.copyFileSync(sourcePath, targetPath);
    }
  }
}

/**
 * Main build function
 */
async function main(): Promise<void> {
  console.log('🚀 Starting @research-copilot/plugin build...\n');

  try {
    // Step 1: Clean dist directory
    cleanDist();

    // Step 2: Copy agents
    copyAgents();

    // Step 3: Copy skills (excluding third_party)
    copySkills();

    // Step 4: Copy README
    copyReadme();

    // Step 5: Generate platform metadata (Task 3)
    generatePlatformMetadata();

    console.log('\n✅ Build completed successfully!');
  } catch (error) {
    console.error('\n❌ Build failed:', error);
    process.exit(1);
  }
}

// Run the build
main();
