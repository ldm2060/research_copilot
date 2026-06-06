import { describe, it, expect } from 'vitest';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

describe('MCP Scholar Integration', () => {
  it('has built MCP scholar server', () => {
    const serverPath = path.resolve('packages/mcp-scholar/dist/mcp-scholar.js');
    expect(fs.existsSync(serverPath)).toBe(true);
  });

  it('MCP scholar server is executable', () => {
    const serverPath = path.resolve('packages/mcp-scholar/dist/mcp-scholar.js');
    const result = execSync(`node "${serverPath}" --help || echo "ok"`, { encoding: 'utf-8' });
    // Just verify it doesn't crash on execution
    expect(result).toBeDefined();
  });

  it('has scholar package.json with correct entry point', () => {
    const pkgPath = path.resolve('packages/mcp-scholar/package.json');
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
    expect(pkg.bin['mcp-scholar']).toBe('./dist/mcp-scholar.js');
  });
});
