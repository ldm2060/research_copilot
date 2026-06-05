// Shared result shape for every literature backend. Each backend MUST set
// `source` to its own tag (e.g. "arxiv", "dblp", "scholar", "arxivsub") so the
// facade can attribute every result to the backend that produced it.
export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year?: number;
  abstract?: string;
  url?: string;
  source: string;
}
