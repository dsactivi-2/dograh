/**
 * Typed Text-Chat Eval Harness client (P2).
 */

import { client } from "@/client/client.gen";

export type EvalAssertion = {
  type:
    | "response_contains"
    | "response_not_contains"
    | "disposition_equals"
    | "gathered_key_equals"
    | "gathered_key_exists";
  value?: unknown;
  key?: string | null;
  case_insensitive?: boolean;
};

export type TextEvalScenario = {
  name: string;
  workflow_id: number;
  initial_context?: Record<string, unknown>;
  turns: Array<{ user: string; assertions?: EvalAssertion[] }>;
  final_assertions?: EvalAssertion[];
  run_qa?: boolean;
};

export type AssertionResult = {
  type: string;
  passed: boolean;
  detail: string;
  expected?: unknown;
  actual?: unknown;
};

export type TextEvalRunResponse = {
  scenario_name: string;
  workflow_id: number;
  workflow_run_id: number | null;
  passed: boolean;
  turns: Array<{
    index: number;
    user: string;
    assistant: string;
    assertions: AssertionResult[];
    passed: boolean;
  }>;
  final_assertions: AssertionResult[];
  gathered_context: Record<string, unknown>;
  error?: string | null;
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

export async function runTextEval(
  scenario: TextEvalScenario,
): Promise<TextEvalRunResponse> {
  const res = await client.post({
    url: "/api/v1/evals/text/run",
    body: scenario,
  });
  if (res.error) throw new Error(errMsg(res.error, "Eval run failed"));
  return res.data as TextEvalRunResponse;
}

// --- Voice eval (P6) ---

export type VoiceScoreRunRequest = {
  workflow_run_id: number;
  assertions?: Array<Record<string, unknown>>;
  success_codes?: string[];
  pass_score?: number;
  include_qa?: boolean;
};

export type VoiceScoreResult = {
  mode: string;
  run_id: number;
  workflow_id: number | null;
  run_mode: string | null;
  is_completed: boolean;
  score: number;
  passed: boolean;
  pass_score: number;
  transcript: string;
  transcript_chars: number;
  has_transcript: boolean;
  disposition: string | null;
  disposition_success: boolean;
  success_codes: string[];
  assertions_total: number;
  assertions_passed: number;
  assertion_pass_rate: number | null;
  assertion_results: AssertionResult[];
  qa_score: number | null;
  qa_tags: string[];
  qa?: Record<string, unknown> | null;
  error?: string | null;
  scenario_name?: string | null;
};

export type VoiceSessionCreateRequest = {
  workflow_id: number;
  scenario_name?: string;
  initial_context?: Record<string, unknown>;
  max_duration_seconds?: number;
  assertions?: Array<Record<string, unknown>>;
  success_codes?: string[];
  pass_score?: number;
  tags?: string[];
};

export type VoiceSessionCreateResponse = {
  workflow_id: number;
  workflow_run_id: number;
  mode: string;
  scenario_name: string;
  max_duration_hint_seconds: number;
  signaling_path: string;
  guards: Record<string, unknown>;
  assertions: Array<Record<string, unknown>>;
  success_codes: string[];
  pass_score: number;
  message: string;
};

export async function scoreVoiceRun(
  body: VoiceScoreRunRequest,
): Promise<VoiceScoreResult> {
  const res = await client.post({
    url: "/api/v1/evals/voice/score-run",
    body,
  });
  if (res.error) throw new Error(errMsg(res.error, "Voice score failed"));
  return res.data as VoiceScoreResult;
}

export async function createVoiceEvalSession(
  body: VoiceSessionCreateRequest,
): Promise<VoiceSessionCreateResponse> {
  const res = await client.post({
    url: "/api/v1/evals/voice/sessions",
    body,
  });
  if (res.error) throw new Error(errMsg(res.error, "Voice session create failed"));
  return res.data as VoiceSessionCreateResponse;
}

export async function finalizeVoiceEvalSession(
  runId: number,
  body?: {
    assertions?: Array<Record<string, unknown>>;
    success_codes?: string[];
    pass_score?: number;
    include_qa?: boolean;
  },
): Promise<VoiceScoreResult> {
  const res = await client.post({
    url: `/api/v1/evals/voice/sessions/${runId}/finalize`,
    body: body || {},
  });
  if (res.error) throw new Error(errMsg(res.error, "Voice finalize failed"));
  return res.data as VoiceScoreResult;
}

export type VoiceGuardsStatus = {
  organization_id?: number;
  allowed: boolean;
  enabled: boolean;
  recent_session_count?: number;
  remaining_after?: number;
  max_sessions_per_org_hour: number;
  max_duration_hint_seconds: number;
  hard_max_duration_seconds: number;
  max_batch: number;
  code?: string;
  message?: string;
};

export async function fetchVoiceGuards(): Promise<VoiceGuardsStatus> {
  const res = await client.get({ url: "/api/v1/evals/voice/guards" });
  if (res.error) throw new Error(errMsg(res.error, "Voice guards failed"));
  return res.data as VoiceGuardsStatus;
}
