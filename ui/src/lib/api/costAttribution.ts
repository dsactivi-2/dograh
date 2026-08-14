/**
 * Typed Cost Attribution client (P3).
 * Stable surface for /api/v1/cost-attribution/* until OpenAPI regen.
 */

import { client } from "@/client/client.gen";

export type CostGroupBy = "workflow" | "campaign" | "definition";

export type CostBucket = {
  key: string;
  label: string;
  group_type: "workflow" | "campaign" | "definition" | "unattributed";
  workflow_id: number | null;
  campaign_id: number | null;
  definition_id: number | null;
  run_count: number;
  runs_with_cost: number;
  runs_missing_cost: number;
  total_duration_seconds: number;
  total_cost_usd: number | null;
  total_charge_usd: number | null;
  total_dograh_tokens: number;
  avg_cost_usd: number | null;
  cost_coverage_pct: number;
};

export type CostAttributionSummary = {
  from_date: string;
  to_date: string;
  timezone: string;
  workflow_id: number | null;
  campaign_id: number | null;
  group_by: CostGroupBy;
  total_runs: number;
  runs_with_cost: number;
  runs_missing_cost: number;
  cost_coverage_pct: number;
  total_duration_seconds: number;
  total_cost_usd: number | null;
  total_charge_usd: number | null;
  total_dograh_tokens: number;
  buckets: CostBucket[];
  notes: string[];
};

export type CostAttributionQuery = {
  from_date: string;
  to_date: string;
  timezone?: string;
  workflow_id?: number | null;
  campaign_id?: number | null;
  group_by?: CostGroupBy;
};

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err === "object" && err && "detail" in err) {
    return String((err as { detail: unknown }).detail);
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export async function fetchCostAttributionSummary(
  q: CostAttributionQuery,
): Promise<CostAttributionSummary> {
  const res = await client.get({
    url: "/api/v1/cost-attribution/summary",
    query: {
      from_date: q.from_date,
      to_date: q.to_date,
      timezone: q.timezone || "UTC",
      group_by: q.group_by || "workflow",
      ...(q.workflow_id != null ? { workflow_id: q.workflow_id } : {}),
      ...(q.campaign_id != null ? { campaign_id: q.campaign_id } : {}),
    },
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "Cost attribution summary failed"));
  }
  return res.data as CostAttributionSummary;
}
