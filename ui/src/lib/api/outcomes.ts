/**
 * Typed Outcomes API client (P0).
 *
 * OpenAPI codegen requires a live backend (`npm run generate-client`).
 * Until the full client is regenerated against a running API with the new
 * routes, this module is the stable typed surface for `/api/v1/outcomes/*`.
 */

import { client } from "@/client/client.gen";

export type QaNodeOutcome = {
  node_id: string;
  node_name: string;
  score: number | null;
  tags: string[];
  summary: string;
  error?: string | null;
  raw?: Record<string, unknown>;
};

export type QaRunOutcome = {
  schema_version: 1;
  run_id: number;
  workflow_id: number | null;
  has_qa: boolean;
  overall_score: number | null;
  tags: string[];
  nodes: QaNodeOutcome[];
  errors: string[];
  source_keys: string[];
};

export type OutcomeRunRow = {
  run_id: number;
  workflow_id: number;
  workflow_name: string;
  created_at: string | null;
  is_completed: boolean;
  disposition: string;
  phone_number: string;
  duration_seconds: number | null;
  call_tags: string[];
  qa: QaRunOutcome;
};

export type DispositionBucket = {
  disposition: string;
  count: number;
  percentage: number;
};

export type OutcomesSummary = {
  from_date: string;
  to_date: string;
  timezone: string;
  workflow_id: number | null;
  total_runs: number;
  completed_runs: number;
  disposition_distribution: DispositionBucket[];
  qa_coverage: {
    runs_with_qa: number;
    runs_without_qa: number;
    coverage_pct: number;
  };
  average_qa_score: number | null;
  top_qa_tags: Array<{ tag: string; count: number }>;
};

export type OutcomesListResponse = {
  total: number;
  page: number;
  limit: number;
  runs: OutcomeRunRow[];
};

export type OutcomesQuery = {
  from_date: string;
  to_date: string;
  timezone?: string;
  workflow_id?: number | null;
  page?: number;
  limit?: number;
};

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err === "object" && err && "detail" in err) {
    return String((err as { detail: unknown }).detail);
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export async function fetchOutcomesSummary(
  q: OutcomesQuery,
): Promise<OutcomesSummary> {
  const res = await client.get({
    url: "/api/v1/outcomes/summary",
    query: {
      from_date: q.from_date,
      to_date: q.to_date,
      timezone: q.timezone || "UTC",
      ...(q.workflow_id != null ? { workflow_id: q.workflow_id } : {}),
    },
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "Outcomes summary failed"));
  }
  return res.data as OutcomesSummary;
}

export async function fetchOutcomesRuns(
  q: OutcomesQuery,
): Promise<OutcomesListResponse> {
  const res = await client.get({
    url: "/api/v1/outcomes/runs",
    query: {
      from_date: q.from_date,
      to_date: q.to_date,
      timezone: q.timezone || "UTC",
      page: q.page ?? 1,
      limit: q.limit ?? 50,
      ...(q.workflow_id != null ? { workflow_id: q.workflow_id } : {}),
    },
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "Outcomes runs failed"));
  }
  return res.data as OutcomesListResponse;
}

export async function fetchRunQa(runId: number): Promise<QaRunOutcome> {
  const res = await client.get({
    url: `/api/v1/outcomes/runs/${runId}/qa`,
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "QA fetch failed"));
  }
  return res.data as QaRunOutcome;
}
