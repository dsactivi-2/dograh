"use client";

import { FlaskConical, Mic, Play } from "lucide-react";
import { useEffect, useState } from "react";

import { getWorkflowOptionsApiV1OrganizationsReportsWorkflowsGet } from "@/client/sdk.gen";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  type TextEvalRunResponse,
  type TextEvalScenario,
  type VoiceScoreResult,
  type VoiceSessionCreateResponse,
  createVoiceEvalSession,
  finalizeVoiceEvalSession,
  fetchVoiceGuards,
  runTextEval,
  scoreVoiceRun,
  type VoiceGuardsStatus,
} from "@/lib/api/evals";
import { useAuth } from "@/lib/auth";

type WorkflowOption = { id: number; name: string };

const DEFAULT_SCENARIO = `{
  "name": "smoke-greeting",
  "workflow_id": 0,
  "initial_context": {},
  "turns": [
    {
      "user": "Hello",
      "assertions": [
        { "type": "response_contains", "value": "hi", "case_insensitive": true }
      ]
    }
  ],
  "final_assertions": []
}`;

const DEFAULT_VOICE_ASSERTIONS = `[
  { "type": "response_contains", "value": "hallo", "case_insensitive": true }
]`;

export default function EvalsPage() {
  const auth = useAuth();
  const [tab, setTab] = useState<"text" | "voice">("text");
  const [guards, setGuards] = useState<VoiceGuardsStatus | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);
  const [workflowId, setWorkflowId] = useState("");
  const [jsonText, setJsonText] = useState(DEFAULT_SCENARIO);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<TextEvalRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // voice state
  const [runIdInput, setRunIdInput] = useState("");
  const [successCodes, setSuccessCodes] = useState("XFER");
  const [voiceAssertions, setVoiceAssertions] = useState(DEFAULT_VOICE_ASSERTIONS);
  const [voiceSession, setVoiceSession] =
    useState<VoiceSessionCreateResponse | null>(null);
  const [voiceResult, setVoiceResult] = useState<VoiceScoreResult | null>(null);
  const [maxDur, setMaxDur] = useState("90");

  useEffect(() => {
    if (!auth.isAuthenticated) return;
    (async () => {
      try {
        const res =
          await getWorkflowOptionsApiV1OrganizationsReportsWorkflowsGet({});
        if (res.data) {
          const list = res.data as WorkflowOption[];
          setWorkflows(list);
          if (list[0]) setWorkflowId(String(list[0].id));
        }
      } catch (e) {
        console.error(e);
      }
    })();
  }, [auth.isAuthenticated]);

  useEffect(() => {
    if (!auth.isAuthenticated || tab !== "voice") return;
    (async () => {
      try {
        setGuards(await fetchVoiceGuards());
      } catch (e) {
        console.error(e);
      }
    })();
  }, [auth.isAuthenticated, tab]);

  const parseAssertions = () => {
    try {
      const a = JSON.parse(voiceAssertions);
      return Array.isArray(a) ? a : [];
    } catch {
      throw new Error("Assertions JSON ungültig");
    }
  };

  const onRunText = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const parsed = JSON.parse(jsonText) as TextEvalScenario;
      if (workflowId) parsed.workflow_id = Number(workflowId);
      if (!parsed.workflow_id) {
        throw new Error("workflow_id erforderlich");
      }
      const res = await runTextEval(parsed);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Eval failed");
    } finally {
      setRunning(false);
    }
  };

  const onScoreRun = async () => {
    setRunning(true);
    setError(null);
    setVoiceResult(null);
    try {
      const id = Number(runIdInput);
      if (!id) throw new Error("workflow_run_id erforderlich");
      const res = await scoreVoiceRun({
        workflow_run_id: id,
        assertions: parseAssertions(),
        success_codes: successCodes
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        pass_score: 70,
        include_qa: true,
      });
      setVoiceResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Score failed");
    } finally {
      setRunning(false);
    }
  };

  const onCreateSession = async () => {
    setRunning(true);
    setError(null);
    setVoiceSession(null);
    setVoiceResult(null);
    try {
      if (!workflowId) throw new Error("Workflow wählen");
      const res = await createVoiceEvalSession({
        workflow_id: Number(workflowId),
        scenario_name: "ui-voice-eval",
        max_duration_seconds: Number(maxDur) || 90,
        assertions: parseAssertions(),
        success_codes: successCodes
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        pass_score: 70,
      });
      setVoiceSession(res);
      setRunIdInput(String(res.workflow_run_id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Session create failed");
    } finally {
      setRunning(false);
    }
  };

  const onFinalize = async () => {
    setRunning(true);
    setError(null);
    try {
      const id = Number(runIdInput || voiceSession?.workflow_run_id);
      if (!id) throw new Error("run_id erforderlich");
      const res = await finalizeVoiceEvalSession(id, {
        assertions: parseAssertions(),
        success_codes: successCodes
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        pass_score: 70,
        include_qa: true,
      });
      setVoiceResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Finalize failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 md:p-8">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <FlaskConical className="h-6 w-6" />
          Eval Harness
        </h1>
        <p className="text-sm text-muted-foreground">
          Text-Chat (P2) und Voice-Score / kurze WebRTC-Sessions (P6). Kein
          Headless-Audio, kein Dual-Role.
        </p>
      </div>

      <div className="flex gap-2">
        <Button
          variant={tab === "text" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("text")}
        >
          Text
        </Button>
        <Button
          variant={tab === "voice" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("voice")}
        >
          <Mic className="mr-1.5 h-4 w-4" />
          Voice
        </Button>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </Card>
      )}

      {tab === "text" && (
        <>
          <Card className="space-y-3 p-4">
            <div className="space-y-1.5">
              <Label>Workflow</Label>
              <Select value={workflowId} onValueChange={setWorkflowId}>
                <SelectTrigger>
                  <SelectValue placeholder="Workflow" />
                </SelectTrigger>
                <SelectContent>
                  {workflows.map((w) => (
                    <SelectItem key={w.id} value={String(w.id)}>
                      {w.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Scenario JSON</Label>
              <Textarea
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                rows={16}
                className="font-mono text-xs"
              />
            </div>
            <Button onClick={onRunText} disabled={running || !workflowId}>
              <Play className="mr-2 h-4 w-4" />
              {running ? "Läuft…" : "Text-Eval starten"}
            </Button>
          </Card>

          {result && (
            <Card className="space-y-3 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                    result.passed
                      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                      : "bg-red-500/15 text-red-700 dark:text-red-300"
                  }`}
                >
                  {result.passed ? "PASSED" : "FAILED"}
                </span>
                <span className="text-sm font-medium">{result.scenario_name}</span>
                {result.workflow_run_id != null && (
                  <span className="text-xs text-muted-foreground">
                    run #{result.workflow_run_id}
                  </span>
                )}
              </div>
              {result.error && (
                <p className="text-sm text-destructive">{result.error}</p>
              )}
              <ul className="space-y-3">
                {result.turns.map((t) => (
                  <li key={t.index} className="rounded-lg border p-3 text-sm">
                    <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
                      <span>Turn {t.index + 1}</span>
                      <span
                        className={
                          t.passed ? "text-emerald-600" : "text-red-600"
                        }
                      >
                        {t.passed ? "ok" : "fail"}
                      </span>
                    </div>
                    <p>
                      <span className="font-medium">User:</span> {t.user}
                    </p>
                    <p className="mt-1 text-muted-foreground">
                      <span className="font-medium text-foreground">
                        Assistant:
                      </span>{" "}
                      {t.assistant || "—"}
                    </p>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}

      {tab === "voice" && (
        <>
          <Card className="space-y-3 p-4">
            <p className="text-sm text-muted-foreground">
              <strong>A)</strong> Bestehenden Voice-Run scoren (kostenlos) ·{" "}
              <strong>B)</strong> Kurze SMALLWEBRTC-Session anlegen (Rate-Limit),
              im Workflow-Player sprechen, dann finalize.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Workflow (für Session)</Label>
                <Select value={workflowId} onValueChange={setWorkflowId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Workflow" />
                  </SelectTrigger>
                  <SelectContent>
                    {workflows.map((w) => (
                      <SelectItem key={w.id} value={String(w.id)}>
                        {w.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Max Dauer Hint (s, ≤180)</Label>
                <Input
                  value={maxDur}
                  onChange={(e) => setMaxDur(e.target.value)}
                  type="number"
                  min={15}
                  max={180}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Run ID (score / finalize)</Label>
                <Input
                  value={runIdInput}
                  onChange={(e) => setRunIdInput(e.target.value)}
                  placeholder="z.B. 12345"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Success-Codes</Label>
                <Input
                  value={successCodes}
                  onChange={(e) => setSuccessCodes(e.target.value)}
                  placeholder="XFER, SALE"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Assertions JSON</Label>
              <Textarea
                value={voiceAssertions}
                onChange={(e) => setVoiceAssertions(e.target.value)}
                rows={5}
                className="font-mono text-xs"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={onScoreRun}
                disabled={running || !runIdInput}
              >
                Score Run
              </Button>
              <Button onClick={onCreateSession} disabled={running || !workflowId}>
                <Mic className="mr-1.5 h-4 w-4" />
                Session anlegen
              </Button>
              <Button
                variant="outline"
                onClick={onFinalize}
                disabled={running || !(runIdInput || voiceSession)}
              >
                Finalize
              </Button>
            </div>
          </Card>

          {voiceSession && (
            <Card className="space-y-2 p-4 text-sm">
              <p className="font-medium">
                Session run #{voiceSession.workflow_run_id}
              </p>
              <p className="text-muted-foreground">
                Dauer-Hint: {voiceSession.max_duration_hint_seconds}s · Mode:{" "}
                {voiceSession.mode}
              </p>
              <p className="font-mono text-xs break-all">
                Signaling: {voiceSession.signaling_path}
              </p>
              <p className="text-xs text-muted-foreground">
                {voiceSession.message} Öffne den Workflow und starte den Run im
                Browser (WebRTC), oder nutze den bestehenden Voice-Player mit
                dieser Run-ID.
              </p>
            </Card>
          )}

          {voiceResult && (
            <Card className="space-y-3 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                    voiceResult.passed
                      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                      : "bg-red-500/15 text-red-700 dark:text-red-300"
                  }`}
                >
                  {voiceResult.passed ? "PASSED" : "FAILED"} ·{" "}
                  {voiceResult.score}%
                </span>
                <span className="text-xs text-muted-foreground">
                  run #{voiceResult.run_id}
                  {voiceResult.disposition
                    ? ` · ${voiceResult.disposition}`
                    : ""}
                </span>
              </div>
              <div className="grid gap-2 text-xs sm:grid-cols-3">
                <div>
                  Assertions: {voiceResult.assertions_passed}/
                  {voiceResult.assertions_total}
                </div>
                <div>
                  Disposition ok:{" "}
                  {voiceResult.disposition_success ? "yes" : "no"}
                </div>
                <div>
                  QA score:{" "}
                  {voiceResult.qa_score != null ? voiceResult.qa_score : "—"}
                </div>
              </div>
              {voiceResult.transcript ? (
                <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">
                  {voiceResult.transcript}
                </pre>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Kein Transcript (Call noch nicht beendet oder keine RTF-Events).
                </p>
              )}
              {voiceResult.qa_tags?.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  QA-Tags: {voiceResult.qa_tags.join(", ")}
                </p>
              )}
            </Card>
          )}

          <Card className="p-4 text-xs text-muted-foreground">
            <p className="mb-1 font-medium text-foreground">Cost Guards</p>
            <ul className="list-inside list-disc space-y-0.5">
              <li>Max 10 Voice-Sessions pro Org / Stunde (VEVAL-/VTRAIN-)</li>
              <li>Keine Batch-Voice-Jobs · max duration hint 180s</li>
              <li>Quota (authorize_workflow_run_start) bleibt aktiv</li>
              <li>BLOCKED: Headless-Audio-Inject, Dual-Role (Looptalk removed)</li>
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
