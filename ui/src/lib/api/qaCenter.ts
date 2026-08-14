/**
 * Typed QA Center + Compliance client (P4).
 *
 * OpenAPI codegen requires a live backend (`npm run generate-client`).
 * Until then this is the stable typed surface for `/api/v1/qa-center/*`.
 */

import { client } from "@/client/client.gen";

export type QaNodeOutcome = {
  node_id: string;
  node_name: string;
  score: number | null;
  tags: string[];
  summary: string;
  sentiment?: string | null;
  error?: string | null;
};

export type QaRunOutcome = {
  schema_version: 1;
  run_id: number;
  workflow_id: number | null;
  has_qa: boolean;
  overall_score: number | null;
  sentiment?: string | null;
  tags: string[];
  nodes: QaNodeOutcome[];
  errors: string[];
  source_keys: string[];
};

export type ComplianceFlag = {
  key: string;
  label: string;
  status: "pass" | "fail" | "unknown";
  source: string;
  detail: string;
};

export type QaManualOverride = {
  schema_version: 1;
  overall_score: number | null;
  sentiment: string | null;
  tags: string[];
  summary: string;
  notes: string;
  compliance_flags: Record<string, boolean | null>;
  reviewer_user_id: number;
  reviewer_email: string | null;
  created_at: string;
};

export type QaCenterRunRow = {
  run_id: number;
  workflow_id: number;
  workflow_name: string;
  created_at: string | null;
  is_completed: boolean;
  disposition: string;
  phone_number: string;
  duration_seconds: number | null;
  qa: QaRunOutcome;
  effective_score: number | null;
  effective_sentiment: string | null;
  effective_tags: string[];
  effective_summary: string;
  has_override: boolean;
  override: QaManualOverride | null;
  needs_review: boolean;
  review_reasons: string[];
  compliance_flags: ComplianceFlag[];
  compliance_fail_count: number;
  compliance_unknown_count: number;
};

export type QaCenterSummary = {
  from_date: string;
  to_date: string;
  timezone: string;
  workflow_id: number | null;
  total_runs: number;
  runs_with_qa: number;
  runs_without_qa: number;
  coverage_pct: number;
  average_score: number | null;
  low_score_count: number;
  problem_tag_count: number;
  override_count: number;
  needs_review_count: number;
  compliance_fail_runs: number;
  top_tags: Array<{ tag: string; count: number }>;
  sentiment_distribution: Array<{
    sentiment: string;
    count: number;
    percentage: number;
  }>;
  score_distribution: Array<{ bucket: string; count: number }>;
  compliance_summary: Array<{
    key: string;
    label: string;
    pass_count: number;
    fail_count: number;
    unknown_count: number;
  }>;
  max_score_threshold: number;
  problem_tags: string[];
};

export type QaCenterQueueResponse = {
  total: number;
  page: number;
  limit: number;
  max_score_threshold: number;
  problem_tags: string[];
  runs: QaCenterRunRow[];
};

export type QaCenterDetailResponse = {
  run: QaCenterRunRow;
  audit_history: Array<Record<string, unknown>>;
};

export type QaOverrideBody = {
  overall_score?: number | null;
  sentiment?: string | null;
  tags?: string[];
  summary?: string;
  notes?: string;
  compliance_flags?: Record<string, boolean | null>;
};

export type QaRerunResponse = {
  run_id: number;
  status: "queued" | "unavailable";
  message: string;
};

export type QaCenterQuery = {
  from_date: string;
  to_date: string;
  timezone?: string;
  workflow_id?: number | null;
  max_score?: number;
  page?: number;
  limit?: number;
  only_needs_review?: boolean;
};

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err === "object" && err && "detail" in err) {
    return String((err as { detail: unknown }).detail);
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export async function fetchQaCenterSummary(
  q: QaCenterQuery,
): Promise<QaCenterSummary> {
  const res = await client.get({
    url: "/api/v1/qa-center/summary",
    query: {
      from_date: q.from_date,
      to_date: q.to_date,
      timezone: q.timezone || "UTC",
      max_score: q.max_score ?? 6,
      ...(q.workflow_id != null ? { workflow_id: q.workflow_id } : {}),
    },
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "QA Center summary failed"));
  }
  return res.data as QaCenterSummary;
}

export async function fetchQaCenterQueue(
  q: QaCenterQuery,
): Promise<QaCenterQueueResponse> {
  const res = await client.get({
    url: "/api/v1/qa-center/queue",
    query: {
      from_date: q.from_date,
      to_date: q.to_date,
      timezone: q.timezone || "UTC",
      max_score: q.max_score ?? 6,
      only_needs_review: q.only_needs_review ?? true,
      page: q.page ?? 1,
      limit: q.limit ?? 50,
      ...(q.workflow_id != null ? { workflow_id: q.workflow_id } : {}),
    },
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "QA Center queue failed"));
  }
  return res.data as QaCenterQueueResponse;
}

export async function fetchQaCenterRun(
  runId: number,
): Promise<QaCenterDetailResponse> {
  const res = await client.get({
    url: `/api/v1/qa-center/runs/${runId}`,
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "QA run detail failed"));
  }
  return res.data as QaCenterDetailResponse;
}

export async function saveQaOverride(
  runId: number,
  body: QaOverrideBody,
): Promise<QaCenterDetailResponse> {
  const res = await client.put({
    url: `/api/v1/qa-center/runs/${runId}/override`,
    body,
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "QA override save failed"));
  }
  return res.data as QaCenterDetailResponse;
}

export async function rerunQa(runId: number): Promise<QaRerunResponse> {
  const res = await client.post({
    url: `/api/v1/qa-center/runs/${runId}/rerun`,
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "QA re-run failed"));
  }
  return res.data as QaRerunResponse;
}
