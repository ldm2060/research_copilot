export const KINDS = [
  "literature","ideation","experiment","writing","polish","review","rebuttal"
] as const;
export type Kind = (typeof KINDS)[number];

export const STATUSES = ["planning","in_progress","verify","completed"] as const;
export type Status = (typeof STATUSES)[number];

export type Priority = "P0" | "P1" | "P2" | "P3";

export interface Gap {
  desc: string;
  suggest_kind: Kind;
  status: "open" | "resolved";
}

export interface TaskRecord {
  id: string;            // YYYY-MM-DD-slug
  title: string;
  kind: Kind;
  status: Status;
  priority: Priority;
  venue?: string;
  parent?: string;
  children: string[];
  depends_on: string[];
  gaps: Gap[];
  branch?: string;
  created: string;       // ISO 8601
  updated: string;       // ISO 8601
}

export function isKind(x: string): x is Kind {
  return (KINDS as readonly string[]).includes(x);
}
