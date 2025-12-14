// WebSocket event types from server

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

export interface ResearchEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

// Specific event data types
export interface SearchAndFilterStartedData {
  stage_id: string;
  query: string;
  time_filter?: string;
}

export interface SearchAndFilterCompletedData {
  stage_id: string;
  query: string;
  total_results: number;
  relevant_count: number;
  filtered_out: number;
  avg_relevance_score?: number;
  results: SearchResult[];
}

export interface ScrapeStartedData {
  stage_id: string;
  url: string;
  title: string;
}

export interface ScrapeCompleteData {
  stage_id: string;
  url: string;
  success: boolean;
  error?: string;
}

export interface ExtractionStartedData {
  stage_id: string;
  url: string;
}

export interface ExtractionCompleteData {
  stage_id: string;
  url: string;
  page_type: string;
  title: string;
  error?: string;
}

// Connection state
export type ConnectionState = "disconnected" | "connecting" | "connected";

// Research state
export type ResearchState = "idle" | "researching" | "stopped" | "complete" | "error";

// Stage status
export type StageStatus = "pending" | "in_progress" | "completed" | "failed";

export interface Stage {
  id: string;
  type: "search_and_filter" | "scrape" | "extraction" | "rewriter" | "writing" | "early_stop" | "initializing" | "guardrail";
  status: StageStatus;
  title: string;
  error?: string;
}

export interface EarlyStopData {
  stage_id: string;
  reason: string;
}

export interface WritingStartedData {
  stage_id: string;
}

export interface WritingCompleteData {
  stage_id: string;
}

export interface StoppedData {
  has_data: boolean;
}

export interface RewriterStartedData {
  stage_id: string;
  queries_executed_count: number;
}

export interface RewriterCompleteData {
  stage_id: string;
  action: "continue" | "stop";
  queries_count: number;
  queries?: string[];
}
