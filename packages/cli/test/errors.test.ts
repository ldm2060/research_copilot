import { describe, it, expect } from "vitest";
import { classifyCliError } from "../src/errors.js";
import { buildProgram } from "../src/program.js";
import { applyExitOverride } from "../src/errors.js";

describe("classifyCliError (§16.9)", () => {
  it("maps an illegal FSM transition to exit 2 with a clean message", () => {
    const r = classifyCliError(new Error("illegal transition: completed -> in_progress (allowed: none)"));
    expect(r.exitCode).toBe(2);
    expect(r.message).toMatch(/illegal transition/);
  });
  it("maps ENOENT (missing task/file) to exit 1 with a clean, path-free message", () => {
    const e: any = new Error("ENOENT: no such file or directory, open 'C:/x/.research/tasks/foo/task.json'");
    e.code = "ENOENT"; e.path = "C:/x/.research/tasks/foo/task.json";
    const r = classifyCliError(e);
    expect(r.exitCode).toBe(1);
    expect(r.message).not.toContain("C:/x"); // no leaked absolute path
    expect(r.message).toMatch(/not found/i);
  });
  it("maps commander usage errors to exit 2 (message already printed by commander → null)", () => {
    const e: any = new Error("unknown command"); e.code = "commander.unknownCommand"; e.exitCode = 1;
    const r = classifyCliError(e);
    expect(r.exitCode).toBe(2);
    expect(r.message).toBeNull();
  });
  it("maps commander help/version to exit 0", () => {
    const e: any = new Error("(outputHelp)"); e.code = "commander.helpDisplayed"; e.exitCode = 0;
    expect(classifyCliError(e)).toEqual({ exitCode: 0, message: null });
  });
  it("maps an unknown runtime error to exit 1 with its message", () => {
    expect(classifyCliError(new Error("boom"))).toEqual({ exitCode: 1, message: "boom" });
  });
});

describe("applyExitOverride (subcommand usage → exit 2)", () => {
  it("makes a missing-required-option subcommand error throw a commander error → exit 2", () => {
    const program = buildProgram("/tmp/whatever");
    applyExitOverride(program);
    let caught: unknown;
    try { program.parse(["init"], { from: "user" }); } catch (e) { caught = e; }
    expect(caught).toBeTruthy();
    expect(classifyCliError(caught).exitCode).toBe(2);
  });
  it("makes an unknown subcommand throw → exit 2", () => {
    const program = buildProgram("/tmp/whatever");
    applyExitOverride(program);
    let caught: unknown;
    try { program.parse(["task", "bogus"], { from: "user" }); } catch (e) { caught = e; }
    expect(caught).toBeTruthy();
    expect(classifyCliError(caught).exitCode).toBe(2);
  });
});
