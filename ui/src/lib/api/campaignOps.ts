/**
 * Typed Campaign Control Tower client (P3).
 * Stable surface for /api/v1/campaign-ops/* until OpenAPI regen.
 */

import { client } from "@/client/client.gen";

export type FunnelStage = {
  key: string;
  label: string;
  count: number;
};

export type DispositionBucket = {
  disposition: string;
  count: number;
  percentage: number;
};

export type RetryVisibility = {
  enabled: boolean;
  max_retries: number;
  retry_delay_seconds: number;
  total_with_retry: number;
  max_observed_retry_count: number;
  by_reason: Record<string, number>;
};

export type CircuitBreakerVisibility = {
  enabled: boolean;
  failure_threshold: number;
  window_seconds: number;
  min_calls_in_window: number;
  is_open: boolean | null;
  failure_count: number | null;
  success_count: number | null;
  failure_rate: number | null;
  source: string;
};

export type CampaignOpsRow = {
  campaign_id: number;
  campaign_name: string;
  workflow_id: number;
  workflow_name: string;
  state: string;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  total_rows: number | null;
  processed_rows: number;
  failed_rows: number;
  queued: number;
  processing: number;
  processed: number;
  failed_queued: number;
  total_queued_runs: number;
  runs_total: number;
  runs_completed: number;
  runs_connected: number;
  disposition_distribution: DispositionBucket[];
  retry: RetryVisibility;
  circuit_breaker: CircuitBreakerVisibility;
  recent_logs: Array<Record<string, unknown>>;
};

export type CampaignOpsSummary = {
  from_date: string;
  to_date: string;
  timezone: string;
  campaign_id: number | null;
  workflow_id: number | null;
  campaign_count: number;
  funnel: FunnelStage[];
  disposition_distribution: DispositionBucket[];
  totals: Record<string, number>;
  campaigns: CampaignOpsRow[];
};

export type CampaignOpsQuery = {
  from_date: string;
  to_date: string;
  timezone?: string;
  campaign_id?: number | null;
  workflow_id?: number | null;
};

function errorMessage(err: unknown, fallback: string): string {
  if (typeof err === "object" && err && "detail" in err) {
    return String((err as { detail: unknown }).detail);
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export async function fetchCampaignOpsSummary(
  q: CampaignOpsQuery,
): Promise<CampaignOpsSummary> {
  const res = await client.get({
    url: "/api/v1/campaign-ops/summary",
    query: {
      from_date: q.from_date,
      to_date: q.to_date,
      timezone: q.timezone || "UTC",
      ...(q.campaign_id != null ? { campaign_id: q.campaign_id } : {}),
      ...(q.workflow_id != null ? { workflow_id: q.workflow_id } : {}),
    },
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "Campaign ops summary failed"));
  }
  return res.data as CampaignOpsSummary;
}

export async function fetchCampaignOpsDetail(
  campaignId: number,
  q: Omit<CampaignOpsQuery, "campaign_id" | "workflow_id">,
): Promise<CampaignOpsRow> {
  const res = await client.get({
    url: `/api/v1/campaign-ops/campaigns/${campaignId}`,
    query: {
      from_date: q.from_date,
      to_date: q.to_date,
      timezone: q.timezone || "UTC",
    },
  });
  if (res.error) {
    throw new Error(errorMessage(res.error, "Campaign ops detail failed"));
  }
  return res.data as CampaignOpsRow;
}
