#!/usr/bin/env node
import { buildProgram } from "../src/program.js";
import { classifyCliError } from "../src/errors.js";

const program = buildProgram();
program.exitOverride(); // throw CommanderError instead of process.exit, so we control exit codes
try {
  program.parse(process.argv);
} catch (err) {
  const { exitCode, message } = classifyCliError(err);
  if (message) process.stderr.write(`rc: ${message}\n`);
  process.exit(exitCode);
}
