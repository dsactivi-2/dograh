/**
 * Typed Disposition Taxonomy API client.
 */

import { client } from "@/client/client.gen";

export type DispositionCodeMeta = {
  label: string;
  category: "success" | "neutral" | "failure" | "other";
  description: string;
};

export type DispositionTaxonomy = {
  disposition_codes: string[];
  success_codes: string[];
  code_meta: Record<string, DispositionCodeMeta>;
};

export type DispositionTaxonomyResponse = {
  workflow_id: number;
  workflow_name: string;
  taxonomy: DispositionTaxonomy;
};

export type OrgDispositionSummaryItem = {
  code: string;
  label: string;
  category: string;
  workflow_count: number;
  is_success: boolean;
};

function errMsg(err: unknown, fallback: string): string {
  if (typeof err === "object" && err && "detail" in err) {
    return String((err as { detail: unknown }).detail);
  }
  return fallback;
}

export async function fetchOrgDispositionSummary(): Promise<
  OrgDispositionSummaryItem[]
> {
  const res = await client.get({ url: "/api/v1/disposition-taxonomy/summary" });
  if (res.error) throw new Error(errMsg(res.error, "Disposition summary failed"));
  const data = res.data as { codes: OrgDispositionSummaryItem[] };
  return data.codes || [];
}

export async function fetchWorkflowTaxonomy(
  workflowId: number,
): Promise<DispositionTaxonomyResponse> {
  const res = await client.get({
    url: `/api/v1/disposition-taxonomy/workflows/${workflowId}`,
  });
  if (res.error) throw new Error(errMsg(res.error, "Taxonomy fetch failed"));
  return res.data as DispositionTaxonomyResponse;
}

export async function saveWorkflowTaxonomy(
  workflowId: number,
  taxonomy: DispositionTaxonomy,
): Promise<DispositionTaxonomyResponse> {
  const res = await client.put({
    url: `/api/v1/disposition-taxonomy/workflows/${workflowId}`,
    body: taxonomy,
  });
  if (res.error) throw new Error(errMsg(res.error, "Taxonomy save failed"));
  return res.data as DispositionTaxonomyResponse;
}
