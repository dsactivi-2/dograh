/**
 * Typed Training / Schulung client (P5).
 */

import { client } from "@/client/client.gen";

export type TrainingMode = "shadow" | "text" | "voice";
export type Difficulty = "beginner" | "intermediate" | "advanced";

export type TrainingModule = {
  id: number;
  organization_id: number;
  title: string;
  description: string;
  mode: TrainingMode | string;
  workflow_id: number | null;
  workflow_name: string;
  script_entry_id: number | null;
  success_codes: string[];
  tags: string[];
  difficulty: string;
  pass_score: number;
  content: Record<string, unknown>;
  is_published: boolean;
  created_by_user_id: number;
  created_at: string | null;
  best_score: number | null;
  attempts_count: number;
  completed: boolean;
};

export type TrainingModuleList = {
  total: number;
  items: TrainingModule[];
};

export type TrainingAttempt = {
  id: number;
  module_id: number;
  module_title: string;
  user_id: number;
  mode: string;
  score: number;
  passed: boolean;
  result: Record<string, unknown>;
  workflow_run_id: number | null;
  created_at: string | null;
};

export type TrainingProgress = {
  organization_id: number;
  user_id: number;
  modules_total: number;
  modules_completed: number;
  completion_pct: number;
  average_best_score: number | null;
  attempts_total: number;
  modules: Array<{
    module_id: number;
    title: string;
    mode: string;
    difficulty: string;
    pass_score: number;
    attempts_count: number;
    best_score: number | null;
    last_score: number | null;
    completed: boolean;
    last_attempt_at: string | null;
  }>;
};

export type ShadowQuizQuestion = {
  id: string;
  prompt: string;
  options: Array<{ id: string; label: string }>;
  explanation?: string;
};

function errMsg(err: unknown, fallback: string): string {
  if (typeof err === "object" && err && "detail" in err) {
    const d = (err as { detail: unknown }).detail;
    if (typeof d === "object" && d !== null) {
      const o = d as { message?: unknown; code?: unknown };
      if (o.message != null) {
        return o.code != null
          ? `${String(o.code)}: ${String(o.message)}`
          : String(o.message);
      }
      try {
        return JSON.stringify(d);
      } catch {
        return fallback;
      }
    }
    if (typeof d === "string") return d;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export async function listTrainingModules(opts?: {
  mode?: string;
  published_only?: boolean;
}): Promise<TrainingModuleList> {
  const res = await client.get({
    url: "/api/v1/training/modules",
    query: {
      published_only: opts?.published_only ?? true,
      ...(opts?.mode ? { mode: opts.mode } : {}),
      limit: 100,
    },
  });
  if (res.error) throw new Error(errMsg(res.error, "Modules load failed"));
  return res.data as TrainingModuleList;
}

export async function createTrainingModule(body: {
  title: string;
  description?: string;
  mode: TrainingMode;
  workflow_id?: number | null;
  success_codes?: string[];
  tags?: string[];
  difficulty?: Difficulty;
  pass_score?: number;
  content?: Record<string, unknown>;
  is_published?: boolean;
}): Promise<TrainingModule> {
  const res = await client.post({
    url: "/api/v1/training/modules",
    body,
  });
  if (res.error) throw new Error(errMsg(res.error, "Create module failed"));
  return res.data as TrainingModule;
}

export async function fetchTrainingProgress(): Promise<TrainingProgress> {
  const res = await client.get({ url: "/api/v1/training/progress" });
  if (res.error) throw new Error(errMsg(res.error, "Progress failed"));
  return res.data as TrainingProgress;
}

export async function completeShadowModule(
  moduleId: number,
  answers: Array<{ question_id: string; selected_option_ids: string[] }>,
): Promise<TrainingAttempt> {
  const res = await client.post({
    url: `/api/v1/training/modules/${moduleId}/shadow/complete`,
    body: { answers },
  });
  if (res.error) throw new Error(errMsg(res.error, "Shadow complete failed"));
  return res.data as TrainingAttempt;
}

export async function runTextDrill(
  moduleId: number,
): Promise<TrainingAttempt> {
  const res = await client.post({
    url: `/api/v1/training/modules/${moduleId}/text/run`,
    body: {},
  });
  if (res.error) throw new Error(errMsg(res.error, "Text drill failed"));
  return res.data as TrainingAttempt;
}

export async function listMyAttempts(moduleId?: number): Promise<{
  total: number;
  items: TrainingAttempt[];
}> {
  const res = await client.get({
    url: "/api/v1/training/attempts",
    query: {
      limit: 50,
      ...(moduleId != null ? { module_id: moduleId } : {}),
    },
  });
  if (res.error) throw new Error(errMsg(res.error, "Attempts failed"));
  return res.data as { total: number; items: TrainingAttempt[] };
}

export type VoiceDrillStartResponse = {
  module_id: number;
  workflow_id: number;
  workflow_run_id: number;
  mode: string;
  max_duration_hint_seconds: number;
  signaling_path: string;
  guards: Record<string, unknown>;
  message: string;
};

export async function startVoiceDrill(
  moduleId: number,
  opts?: { max_duration_seconds?: number },
): Promise<VoiceDrillStartResponse> {
  const res = await client.post({
    url: `/api/v1/training/modules/${moduleId}/voice/start`,
    body: opts || {},
  });
  if (res.error) throw new Error(errMsg(res.error, "Voice start failed"));
  return res.data as VoiceDrillStartResponse;
}

export async function completeVoiceDrill(
  moduleId: number,
  workflowRunId: number,
  includeQa = true,
): Promise<TrainingAttempt> {
  const res = await client.post({
    url: `/api/v1/training/modules/${moduleId}/voice/complete`,
    body: { workflow_run_id: workflowRunId, include_qa: includeQa },
  });
  if (res.error) throw new Error(errMsg(res.error, "Voice complete failed"));
  return res.data as TrainingAttempt;
}

