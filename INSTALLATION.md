# Installation Guide

Research-copilot can be installed in multiple ways depending on your needs.

## Method 1: NPM (Recommended)

Install globally:
```bash
npm install -g research-copilot
```

Use in a project:
```bash
npm install --save-dev research-copilot
```

Verify installation:
```bash
rc --version
```

## Method 2: pnpm

```bash
pnpm add -g research-copilot
```

## Method 3: Yarn

```bash
yarn global add research-copilot
```

## Method 4: npx (No Installation)

Run without installing:
```bash
npx research-copilot init --user your-name --claude
```

Perfect for trying out or one-time use.

## Method 5: From Source (Development)

Clone and build:
```bash
git clone https://github.com/ldm2060/research_copilot.git
cd research_copilot
pnpm install
pnpm build
```

Run locally:
```bash
node packages/cli/dist/rc.js init --user your-name --claude
```

Or link globally:
```bash
cd packages/cli
npm link
rc --version
```

## Method 6: GitHub Releases (Coming Soon)

Download pre-built archives from [GitHub Releases](https://github.com/ldm2060/research_copilot/releases):

- **Windows:** `research-copilot-v1.0.0-win.zip`
- **Linux:** `research-copilot-v1.0.0-linux.tar.gz`
- **macOS:** `research-copilot-v1.0.0-macos.tar.gz`

Extract and add to PATH:
```bash
# Linux/macOS
tar -xzf research-copilot-v1.0.0-linux.tar.gz
export PATH=$PATH:$(pwd)/research-copilot/bin

# Windows (PowerShell)
Expand-Archive research-copilot-v1.0.0-win.zip
$env:PATH += ";$(pwd)\research-copilot\bin"
```

## Platform-Specific Notes

### Windows
- Requires Node.js 18+ (download from [nodejs.org](https://nodejs.org))
- Git must be installed for `rc sync` to work

### Linux
```bash
# Debian/Ubuntu
sudo apt install nodejs npm git

# Fedora/RHEL
sudo dnf install nodejs npm git

# Install research-copilot
npm install -g research-copilot
```

### macOS
```bash
# Using Homebrew
brew install node git

# Install research-copilot
npm install -g research-copilot
```

## Verifying Installation

Check that all components work:
```bash
# CLI available
rc --version

# MCP servers available
npx @research-copilot/mcp-pdf --help 2>&1 | head -5
npx @research-copilot/mcp-scholar --help 2>&1 | head -5

# Git available (required for skillpacks)
git --version
```

## Troubleshooting

### Permission Errors (npm global install on Linux/macOS)

Use npx instead, or configure npm to install globally without sudo:
```bash
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### Command Not Found After Install

Ensure npm global bin directory is in PATH:
```bash
# Check where npm installs global packages
npm config get prefix

# Add to PATH (Linux/macOS)
export PATH=$PATH:$(npm config get prefix)/bin

# Add to PATH (Windows PowerShell)
$env:PATH += ";$(npm config get prefix)"
```

### Node Version Issues

Research-copilot requires Node.js 18+:
```bash
# Check version
node --version

# If too old, upgrade via nvm (Linux/macOS)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20

# Or via nvm-windows (Windows)
# Download from https://github.com/coreybutler/nvm-windows/releases
nvm install 20
nvm use 20
```

## Next Steps

After installation, initialize your first project:
```bash
mkdir my-research-project
cd my-research-project
git init
rc init --user your-name --claude
```

See the main [README](./README.md) for usage documentation.

### Plugin integration and upgrades

`rc init` is safe to run more than once. On a new project it initializes Research Copilot; on an older Research Copilot project it reconciles missing or outdated managed configuration while preserving existing tasks, specs, workspace files, user hooks, user agents, and unrelated MCP servers.

For a fresh install:

```bash
npm install -g @research-copilot/cli
rc init --user your-name --claude
rc doctor
```

For an existing project upgrading from an older version:

```bash
npm install -g @research-copilot/cli@latest
rc doctor
rc doctor --fix
rc doctor
```

When Claude Code support is enabled, `rc init` and `rc doctor --fix` synchronize the companion npm plugin package to the CLI version:

```bash
npm install -g @research-copilot/plugin@<cli-version>
```

The plugin synchronization is a packaging/version check. Research Copilot's project-local Claude Code configuration remains the reliable runtime path, so plugin install or Claude Code plugin-list warnings do not block normal initialization unless `--strict-plugin` is used.

Use `--skip-plugin` for offline or CI environments:

```bash
rc init --user your-name --claude --skip-plugin
rc doctor --skip-plugin
```

Use `--strict-plugin` when release validation should fail if the npm plugin is missing or out of sync:

```bash
rc doctor --strict-plugin
```
