#!/usr/bin/env node
// Bump version across all packages (cross-platform)

import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const rootDir = join(__dirname, '..');

const version = process.argv[2];

if (!version) {
  console.error('Usage: node scripts/bump-version.js <version>');
  console.error('Example: node scripts/bump-version.js 1.0.1');
  process.exit(1);
}

// Validate semver format
if (!/^\d+\.\d+\.\d+$/.test(version)) {
  console.error('Error: Version must be in semver format (e.g., 1.0.1)');
  process.exit(1);
}

console.log(`Bumping all packages to version ${version}...`);

// Find all package.json files in packages/*/
const packagesDir = join(rootDir, 'packages');
const packages = readdirSync(packagesDir).filter(name => {
  const pkgPath = join(packagesDir, name);
  return statSync(pkgPath).isDirectory();
});

for (const pkgName of packages) {
  const pkgJsonPath = join(packagesDir, pkgName, 'package.json');
  try {
    console.log(`  Updating packages/${pkgName}/package.json`);
    const pkg = JSON.parse(readFileSync(pkgJsonPath, 'utf8'));
    pkg.version = version;
    writeFileSync(pkgJsonPath, JSON.stringify(pkg, null, 2) + '\n');
  } catch (err) {
    console.error(`  Error updating ${pkgJsonPath}: ${err.message}`);
  }
}

console.log(`\nDone! All packages updated to version ${version}`);
console.log('\nNext steps:');
console.log(`  1. git add packages/*/package.json`);
console.log(`  2. git commit -m "chore: bump version to ${version}"`);
console.log(`  3. git tag v${version}`);
console.log(`  4. git push origin main --tags`);
