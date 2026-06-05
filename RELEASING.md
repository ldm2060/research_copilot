# Release Process

## Prerequisites

1. NPM account with publish access to @research-copilot scope
2. NPM_TOKEN secret configured in GitHub repository settings

## Steps

### 1. Bump Version

```bash
node scripts/bump-version.js 1.0.1
```

This updates all package.json files to the new version.

### 2. Commit and Tag

```bash
git add packages/*/package.json
git commit -m "chore: bump version to 1.0.1"
git tag v1.0.1
```

### 3. Push to Trigger Publish

```bash
git push origin main
git push origin v1.0.1
```

GitHub Actions will automatically publish to npm when the tag is pushed.

### 4. Verify Publication

Check npm registry:
```bash
npm view research-copilot
npm view @research-copilot/core
npm view @research-copilot/adapters
npm view @research-copilot/mcp-pdf
npm view @research-copilot/mcp-scholar
```

## Version Strategy

Follow semantic versioning (semver):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

All packages are versioned together (monorepo sync).

## Cross-Platform Compatibility

The packages are designed to work across Windows, Linux, and macOS:
- All path operations use Node.js `path` module (cross-platform)
- Shell commands use `execSync` with proper encoding
- File operations use Node.js `fs` module (cross-platform)
- No OS-specific APIs or hardcoded paths

Minimum Node.js version: 18.0.0
