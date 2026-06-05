#!/usr/bin/env node
import { buildProgram } from "../src/program.js";
import { classifyCliError, applyExitOverride } from "../src/errors.js";

const program = buildProgram();
applyExitOverride(program); // throw CommanderError (incl. subcommands) instead of process.exit, so we control exit codes
try {
  program.parse(process.argv);
} catch (err) {
  const { exitCode, message } = classifyCliError(err);
  if (message) process.stderr.write(`rc: ${message}\n`);
  process.exit(exitCode);
}
