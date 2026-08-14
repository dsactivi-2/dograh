/**
 * Typed Script Library + prompt search + definition diff client (P1).
 */

import { client } from "@/client/client.gen";

export type ApprovalStatus = "draft" | "pending" | "approved" | "rejected";

export type ScriptEntry = {
  id: number;
  organization_id: number;
  workflow_id: number;
  workflow_name: string;
  definition_id: number | null;
  title: string;
  description: string;
  tags: string[];
  owner_user_id: number;
  owner_email: string | null;
  approval_status: ApprovalStatus;
  approved_by_user_id: number | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string | null;
};

export type ScriptListResponse = {
  total: number;
  items: ScriptEntry[];
};

export type PromptSearchHit = {
  workflow_id: number;
  workflow_name: string;
  definition_id: number;
  version_number: number | null;
  version_status: string | null;
  node_id: string;
  node_name: string;
  node_type: string;
  prompt_excerpt: string;
  rank: number;
};

export type PromptDiffLine = {
  node_id: string;
  node_name: string;
  field: string;
  before: string;
  after: string;
  change: "added" | "removed" | "changed" | "unchanged";
};

export type DefinitionDiffResponse = {
  definition_a_id: number;
  definition_b_id: number;
  workflow_id_a: number | null;
  workflow_id_b: number | null;
  changes: PromptDiffLine[];
  summary: Record<string, number>;
};

function errMsg(err: unknown, fallback: string): string {
  if (typeof err === "object" && err && "detail" in err) {
    return String((err as { detail: unknown }).detail);
  }
  return fallback;
}

export async function listScripts(params: {
  workflow_id?: number;
  approval_status?: string;
  tag?: string;
  page?: number;
  limit?: number;
}): Promise<ScriptListResponse> {
  const res = await client.get({
    url: "/api/v1/scripts",
    query: {
      ...(params.workflow_id != null ? { workflow_id: params.workflow_id } : {}),
      ...(params.approval_status
        ? { approval_status: params.approval_status }
        : {}),
      ...(params.tag ? { tag: params.tag } : {}),
      page: params.page ?? 1,
      limit: params.limit ?? 50,
    },
  });
  if (res.error) throw new Error(errMsg(res.error, "List scripts failed"));
  return res.data as ScriptListResponse;
}

export async function createScript(body: {
  workflow_id: number;
  title: string;
  description?: string;
  tags?: string[];
  definition_id?: number | null;
}): Promise<ScriptEntry> {
  const res = await client.post({
    url: "/api/v1/scripts",
    body,
  });
  if (res.error) throw new Error(errMsg(res.error, "Create script failed"));
  return res.data as ScriptEntry;
}

export async function updateScript(
  id: number,
  body: {
    title?: string;
    description?: string;
    tags?: string[];
    definition_id?: number | null;
    approval_status?: ApprovalStatus;
  },
): Promise<ScriptEntry> {
  const res = await client.patch({
    url: `/api/v1/scripts/${id}`,
    body,
  });
  if (res.error) throw new Error(errMsg(res.error, "Update script failed"));
  return res.data as ScriptEntry;
}

export async function searchPrompts(
  q: string,
  opts?: { workflow_id?: number; limit?: number },
): Promise<{ query: string; total: number; hits: PromptSearchHit[] }> {
  const res = await client.get({
    url: "/api/v1/scripts/search/prompts",
    query: {
      q,
      ...(opts?.workflow_id != null ? { workflow_id: opts.workflow_id } : {}),
      limit: opts?.limit ?? 40,
    },
  });
  if (res.error) throw new Error(errMsg(res.error, "Prompt search failed"));
  return res.data as { query: string; total: number; hits: PromptSearchHit[] };
}

export async function diffDefinitions(
  definitionA: number,
  definitionB: number,
): Promise<DefinitionDiffResponse> {
  const res = await client.get({
    url: "/api/v1/scripts/diff",
    query: { definition_a: definitionA, definition_b: definitionB },
  });
  if (res.error) throw new Error(errMsg(res.error, "Diff failed"));
  return res.data as DefinitionDiffResponse;
}
