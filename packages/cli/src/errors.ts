export interface CliErrorResult { exitCode: number; message: string | null; }

export function classifyCliError(err: unknown): CliErrorResult {
  const e = err as { code?: string; exitCode?: number; path?: string } | null;
  // Commander errors: it has already printed help/usage to the user.
  if (e && typeof e.code === "string" && e.code.startsWith("commander.")) {
    if (e.code === "commander.helpDisplayed" || e.code === "commander.version") {
      return { exitCode: 0, message: null };
    }
    return { exitCode: 2, message: null }; // usage error
  }
  const raw = err instanceof Error ? err.message : String(err);
  if (/illegal transition/i.test(raw)) return { exitCode: 2, message: raw };
  if (e?.code === "ENOENT" || /ENOENT|no such file/i.test(raw)) {
    return { exitCode: 1, message: "not found: the requested task or a required file does not exist" };
  }
  return { exitCode: 1, message: raw };
}
