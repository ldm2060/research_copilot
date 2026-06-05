export interface McpServerDef { command: string; args: string[]; }

// Hyphenated names are mandatory: Gemini rejects underscores in server names.
export const MCP_SERVERS: Record<string, McpServerDef> = {
  "research-scholar": { command: "npx", args: ["-y", "@research-copilot/mcp-scholar"] },
  "research-pdf": { command: "npx", args: ["-y", "@research-copilot/mcp-pdf"] },
};
