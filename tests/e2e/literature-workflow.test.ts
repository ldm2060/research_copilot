import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { execSync } from 'child_process';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

describe('Literature Workflow E2E', () => {
  let testDir: string;

  beforeAll(async () => {
    // Create test directory in temp
    testDir = path.join(os.tmpdir(), '.test-research-' + Date.now());
    await fs.mkdir(testDir, { recursive: true });
  });

  afterAll(async () => {
    await fs.rm(testDir, { recursive: true, force: true });
  });

  it('completes basic task lifecycle', async () => {
    // Initialize research directory
    const rcPath = path.resolve('packages/cli/dist/rc.js');
    execSync(`node "${rcPath}" init --user test-user`, { cwd: testDir, stdio: 'inherit' });

    // Verify .research directory was created
    const researchDir = path.join(testDir, '.research');
    expect(await fs.stat(researchDir).then(() => true).catch(() => false)).toBe(true);

    // Create task
    const createOutput = execSync(`node "${rcPath}" task create --kind literature --title "Test task"`, {
      cwd: testDir,
      encoding: 'utf-8'
    });
    const taskId = createOutput.trim();
    expect(taskId).toBeTruthy();
    expect(taskId).toMatch(/^\d{4}-\d{2}-\d{2}-/); // Matches date-based format

    // Start task
    execSync(`node "${rcPath}" task start ${taskId}`, { cwd: testDir });

    // Verify task passes gates
    execSync(`node "${rcPath}" task verify ${taskId}`, { cwd: testDir });

    // Transition to verify state
    execSync(`node "${rcPath}" task set-status ${taskId} verify`, { cwd: testDir });

    // Complete task
    execSync(`node "${rcPath}" task complete ${taskId}`, { cwd: testDir });

    // Check completed
    const taskJson = await fs.readFile(path.join(testDir, `.research/tasks/${taskId}/task.json`), 'utf-8');
    const task = JSON.parse(taskJson);
    expect(task.status).toBe('completed');
  }, 60000);
});
