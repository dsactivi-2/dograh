"use client";

import {
  BookOpen,
  CheckCircle2,
  GraduationCap,
  Play,
  Plus,
  RefreshCw,
  Trophy,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getWorkflowOptionsApiV1OrganizationsReportsWorkflowsGet } from "@/client/sdk.gen";
import { Badge } from "@/components/ui/badge";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  type ShadowQuizQuestion,
  type TrainingAttempt,
  type TrainingModule,
  type TrainingProgress,
  completeShadowModule,
  completeVoiceDrill,
  createTrainingModule,
  fetchTrainingProgress,
  listTrainingModules,
  runTextDrill,
  startVoiceDrill,
} from "@/lib/api/training";
import { useAuth } from "@/lib/auth";

type WorkflowOption = { id: number; name: string };

const SAMPLE_SHADOW_CONTENT = {
  script_excerpt:
    "Agent: Guten Tag, hier ist [Name] von [Firma]. Spreche ich mit [Kunde]?\nKunde: Ja.\nAgent: Super — ich rufe an wegen …",
  learning_points: [
    "Zuerst begrüßen und Firma nennen",
    "Identität des Gesprächspartners bestätigen",
    "Erst danach den Anlass nennen",
  ],
  quiz: [
    {
      id: "q1",
      prompt: "Was kommt zuerst im Gespräch?",
      options: [
        { id: "a", label: "Preis und Angebot" },
        { id: "b", label: "Begrüßung + Firmenname" },
        { id: "c", label: "Einwandbehandlung" },
      ],
      correct_option_ids: ["b"],
      explanation: "Begrüßung und Firmenname vor dem Pitch.",
    },
    {
      id: "q2",
      prompt: "Muss die Identität geprüft werden?",
      options: [
        { id: "yes", label: "Ja, vor sensiblen Themen" },
        { id: "no", label: "Nein, spart Zeit" },
      ],
      correct_option_ids: ["yes"],
      explanation: "Compliance: Identity vor Disclosure.",
    },
  ],
};

export default function TrainingPage() {
  const auth = useAuth();
  const [modules, setModules] = useState<TrainingModule[]>([]);
  const [progress, setProgress] = useState<TrainingProgress | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modeFilter, setModeFilter] = useState<string>("all");

  const [selected, setSelected] = useState<TrainingModule | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attempt, setAttempt] = useState<TrainingAttempt | null>(null);
  const [running, setRunning] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  // create form
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newMode, setNewMode] = useState<"shadow" | "text" | "voice">("shadow");
  const [voiceRunId, setVoiceRunId] = useState<number | null>(null);
  const [voiceSignaling, setVoiceSignaling] = useState<string | null>(null);
  const [newWorkflow, setNewWorkflow] = useState("");
  const [newSuccess, setNewSuccess] = useState("XFER");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    if (!auth.isAuthenticated) return;
    setLoading(true);
    setError(null);
    try {
      const [list, prog] = await Promise.all([
        listTrainingModules({
          mode: modeFilter === "all" ? undefined : modeFilter,
          published_only: true,
        }),
        fetchTrainingProgress(),
      ]);
      setModules(list.items || []);
      setProgress(prog);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Training laden fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  }, [auth.isAuthenticated, modeFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!auth.isAuthenticated) return;
    (async () => {
      try {
        const res =
          await getWorkflowOptionsApiV1OrganizationsReportsWorkflowsGet({});
        if (res.data) setWorkflows(res.data as WorkflowOption[]);
      } catch (e) {
        console.error(e);
      }
    })();
  }, [auth.isAuthenticated]);

  const quiz = useMemo((): ShadowQuizQuestion[] => {
    if (!selected || selected.mode !== "shadow") return [];
    const q = (selected.content as { quiz?: ShadowQuizQuestion[] }).quiz;
    return Array.isArray(q) ? q : [];
  }, [selected]);

  const openModule = (m: TrainingModule) => {
    setSelected(m);
    setAnswers({});
    setAttempt(null);
    setActionMsg(null);
    setVoiceRunId(null);
    setVoiceSignaling(null);
  };

  const submitShadow = async () => {
    if (!selected) return;
    setRunning(true);
    setActionMsg(null);
    try {
      const payload = Object.entries(answers).map(([question_id, opt]) => ({
        question_id,
        selected_option_ids: opt ? [opt] : [],
      }));
      // include unanswered as empty
      for (const q of quiz) {
        if (!answers[q.id]) {
          payload.push({ question_id: q.id, selected_option_ids: [] });
        }
      }
      // dedupe by question_id
      const byId = new Map(payload.map((p) => [p.question_id, p]));
      const res = await completeShadowModule(
        selected.id,
        Array.from(byId.values()),
      );
      setAttempt(res);
      setActionMsg(
        res.passed
          ? `Bestanden mit ${res.score}%`
          : `Nicht bestanden (${res.score}%) — Schwelle ${selected.pass_score}%`,
      );
      await load();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setRunning(false);
    }
  };

  const submitText = async () => {
    if (!selected) return;
    setRunning(true);
    setActionMsg(null);
    try {
      const res = await runTextDrill(selected.id);
      setAttempt(res);
      setActionMsg(
        res.passed
          ? `Drill bestanden: ${res.score}%`
          : `Drill nicht bestanden: ${res.score}%`,
      );
      await load();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Text drill failed");
    } finally {
      setRunning(false);
    }
  };

  const submitVoiceStart = async () => {
    if (!selected) return;
    setRunning(true);
    setActionMsg(null);
    try {
      const res = await startVoiceDrill(selected.id, {
        max_duration_seconds: 90,
      });
      setVoiceRunId(res.workflow_run_id);
      setVoiceSignaling(res.signaling_path);
      setActionMsg(
        `Voice-Session run #${res.workflow_run_id} · max ${res.max_duration_hint_seconds}s. WebRTC verbinden, sprechen, dann abschließen.`,
      );
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Voice start failed");
    } finally {
      setRunning(false);
    }
  };

  const submitVoiceComplete = async () => {
    if (!selected || !voiceRunId) return;
    setRunning(true);
    setActionMsg(null);
    try {
      const res = await completeVoiceDrill(selected.id, voiceRunId, true);
      setAttempt(res);
      setActionMsg(
        res.passed
          ? `Voice bestanden: ${res.score}%`
          : `Voice nicht bestanden: ${res.score}%`,
      );
      await load();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Voice complete failed");
    } finally {
      setRunning(false);
    }
  };

  const createModule = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    setActionMsg(null);
    try {
      if (newMode === "shadow") {
        await createTrainingModule({
          title: newTitle.trim(),
          mode: "shadow",
          difficulty: "beginner",
          pass_score: 70,
          content: SAMPLE_SHADOW_CONTENT,
          tags: ["onboarding"],
          success_codes: newSuccess
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        });
      } else if (newMode === "text") {
        if (!newWorkflow) throw new Error("Workflow für Text-Drill wählen");
        await createTrainingModule({
          title: newTitle.trim(),
          mode: "text",
          workflow_id: Number(newWorkflow),
          difficulty: "intermediate",
          pass_score: 70,
          success_codes: newSuccess
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          content: {
            scenario_name: "training-greeting",
            initial_context: {},
            turns: [
              {
                user: "Hallo?",
                assertions: [
                  {
                    type: "response_contains",
                    value: "hallo",
                    case_insensitive: true,
                  },
                ],
              },
            ],
            final_assertions: [],
          },
          tags: ["text-drill"],
        });
      } else {
        if (!newWorkflow) throw new Error("Workflow für Voice-Drill wählen");
        await createTrainingModule({
          title: newTitle.trim(),
          mode: "voice",
          workflow_id: Number(newWorkflow),
          difficulty: "advanced",
          pass_score: 70,
          success_codes: newSuccess
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          content: {
            briefing:
              "Kurzes Voice-Gespräch (≤90s). Begrüße, nenne Firma, prüfe Identität.",
            initial_context: {},
            assertions: [
              {
                type: "response_contains",
                value: "hallo",
                case_insensitive: true,
              },
            ],
            max_duration_hint_seconds: 90,
          },
          tags: ["voice-drill"],
        });
      }
      setNewTitle("");
      setShowCreate(false);
      await load();
      setActionMsg("Modul angelegt");
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const attemptItems = (attempt?.result?.items || []) as Array<{
    question_id: string;
    correct: boolean;
    explanation?: string;
  }>;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 md:p-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <GraduationCap className="h-6 w-6" />
            Training
          </h1>
          <p className="text-sm text-muted-foreground">
            Schulung: Shadow → Text-Drill → Voice (kurz). Success-Set / Assertions / QA-Tags als Lernsignal.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCreate((v) => !v)}
          >
            <Plus className="mr-1.5 h-4 w-4" />
            Modul
          </Button>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw
              className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            Aktualisieren
          </Button>
        </div>
      </div>

      {progress && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Card className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Fortschritt
            </p>
            <p className="mt-1 flex items-center gap-2 text-2xl font-semibold">
              <Trophy className="h-5 w-5 text-amber-500" />
              {progress.completion_pct.toFixed(0)}%
            </p>
            <p className="text-xs text-muted-foreground">
              {progress.modules_completed}/{progress.modules_total} Module
              bestanden
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Ø Best-Score
            </p>
            <p className="mt-1 text-2xl font-semibold">
              {progress.average_best_score != null
                ? `${progress.average_best_score.toFixed(0)}%`
                : "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              über Module mit Versuchen
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Versuche gesamt
            </p>
            <p className="mt-1 text-2xl font-semibold">
              {progress.attempts_total}
            </p>
            <p className="text-xs text-muted-foreground">Shadow + Text + Voice</p>
          </Card>
        </div>
      )}

      {showCreate && (
        <Card className="grid gap-3 p-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Titel</Label>
            <Input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="z.B. Begrüßung & Identität"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Modus</Label>
            <Select
              value={newMode}
              onValueChange={(v) => setNewMode(v as "shadow" | "text" | "voice")}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="shadow">Shadow (Script + Quiz)</SelectItem>
                <SelectItem value="text">Text-Drill (Eval-Harness)</SelectItem>
                <SelectItem value="voice">Voice-Drill (WebRTC)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {(newMode === "text" || newMode === "voice") && (
            <div className="space-y-1.5">
              <Label>Workflow</Label>
              <Select value={newWorkflow} onValueChange={setNewWorkflow}>
                <SelectTrigger>
                  <SelectValue placeholder="Workflow wählen" />
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
          )}
          <div className="space-y-1.5">
            <Label>Success-Codes (kommagetrennt)</Label>
            <Input
              value={newSuccess}
              onChange={(e) => setNewSuccess(e.target.value)}
              placeholder="XFER, SALE"
            />
          </div>
          <div className="md:col-span-2">
            <Button onClick={createModule} disabled={creating || !newTitle.trim()}>
              {creating ? "Anlegen…" : "Modul mit Sample-Inhalt anlegen"}
            </Button>
          </div>
        </Card>
      )}

      <div className="flex items-center gap-3">
        <Label className="text-xs text-muted-foreground">Filter</Label>
        <Select value={modeFilter} onValueChange={setModeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle Modi</SelectItem>
            <SelectItem value="shadow">Shadow</SelectItem>
            <SelectItem value="text">Text</SelectItem>
            <SelectItem value="voice">Voice</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="flex flex-col gap-3 lg:col-span-2">
          {loading && modules.length === 0 ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))
          ) : modules.length === 0 ? (
            <Card className="p-6 text-sm text-muted-foreground">
              Noch keine Module. Lege eins mit Sample-Inhalt an.
            </Card>
          ) : (
            modules.map((m) => (
              <Card
                key={m.id}
                className={`cursor-pointer p-4 transition-colors hover:bg-muted/40 ${
                  selected?.id === m.id ? "ring-2 ring-primary/40" : ""
                }`}
                onClick={() => openModule(m)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-medium">{m.title}</h3>
                    <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                      {m.description || "—"}
                    </p>
                  </div>
                  {m.completed ? (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
                  ) : (
                    <BookOpen className="h-5 w-5 shrink-0 text-muted-foreground" />
                  )}
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <Badge variant="secondary">{m.mode}</Badge>
                  <Badge variant="outline">{m.difficulty}</Badge>
                  {m.best_score != null && (
                    <Badge variant="outline">best {m.best_score}%</Badge>
                  )}
                  <Badge variant="outline">{m.attempts_count}×</Badge>
                </div>
              </Card>
            ))
          )}
        </div>

        <Card className="p-4 lg:col-span-3">
          {!selected ? (
            <div className="flex min-h-[320px] items-center justify-center text-sm text-muted-foreground">
              Modul wählen, um zu üben
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div>
                <h2 className="text-lg font-semibold">{selected.title}</h2>
                <p className="text-sm text-muted-foreground">
                  Pass-Score {selected.pass_score}% ·{" "}
                  {selected.success_codes.length
                    ? `Success: ${selected.success_codes.join(", ")}`
                    : "kein Success-Set"}
                  {selected.workflow_name
                    ? ` · ${selected.workflow_name}`
                    : ""}
                </p>
              </div>

              {selected.mode === "shadow" && (
                <>
                  {(selected.content as { script_excerpt?: string })
                    .script_excerpt && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Script (Shadow)
                      </h3>
                      <Textarea
                        readOnly
                        rows={6}
                        value={String(
                          (selected.content as { script_excerpt?: string })
                            .script_excerpt || "",
                        )}
                        className="font-mono text-xs"
                      />
                    </div>
                  )}
                  {Array.isArray(
                    (selected.content as { learning_points?: string[] })
                      .learning_points,
                  ) && (
                    <ul className="list-inside list-disc text-sm text-muted-foreground">
                      {(
                        (selected.content as { learning_points?: string[] })
                          .learning_points || []
                      ).map((lp) => (
                        <li key={lp}>{lp}</li>
                      ))}
                    </ul>
                  )}
                  <div className="space-y-4">
                    {quiz.map((q) => (
                      <div key={q.id} className="space-y-2">
                        <p className="text-sm font-medium">{q.prompt}</p>
                        <div className="flex flex-col gap-1.5">
                          {q.options.map((opt) => (
                            <label
                              key={opt.id}
                              className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                                answers[q.id] === opt.id
                                  ? "border-primary bg-primary/5"
                                  : "border-border"
                              }`}
                            >
                              <input
                                type="radio"
                                name={q.id}
                                checked={answers[q.id] === opt.id}
                                onChange={() =>
                                  setAnswers((prev) => ({
                                    ...prev,
                                    [q.id]: opt.id,
                                  }))
                                }
                              />
                              {opt.label}
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <Button onClick={submitShadow} disabled={running}>
                    <Play className="mr-1.5 h-4 w-4" />
                    {running ? "Auswerten…" : "Quiz abschicken"}
                  </Button>
                </>
              )}

              {selected.mode === "text" && (
                <>
                  <p className="text-sm text-muted-foreground">
                    Startet den scripted Text-Drill über den Eval-Harness
                    (TEXTCHAT-Run). Score: Assertions 80% + Disposition im
                    Success-Set 20%.
                  </p>
                  <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
                    {JSON.stringify(selected.content, null, 2)}
                  </pre>
                  <Button onClick={submitText} disabled={running}>
                    <Play className="mr-1.5 h-4 w-4" />
                    {running ? "Drill läuft…" : "Text-Drill starten"}
                  </Button>
                </>
              )}


              {selected.mode === "voice" && (
                <>
                  <p className="text-sm text-muted-foreground">
                    Kurzes Voice-Gespräch (WebRTC). Score: Assertions + Disposition
                    im Success-Set + optionale QA-Tags. Cost-Guard: max ~10
                    Sessions/Org/Stunde.
                  </p>
                  {(selected.content as { briefing?: string }).briefing && (
                    <Card className="border-dashed p-3 text-sm">
                      {(selected.content as { briefing?: string }).briefing}
                    </Card>
                  )}
                  <pre className="max-h-40 overflow-auto rounded-md bg-muted p-3 text-xs">
                    {JSON.stringify(selected.content, null, 2)}
                  </pre>
                  <div className="flex flex-wrap gap-2">
                    <Button onClick={submitVoiceStart} disabled={running}>
                      <Play className="mr-1.5 h-4 w-4" />
                      {running ? "…" : "Voice-Session starten"}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={submitVoiceComplete}
                      disabled={running || !voiceRunId}
                    >
                      Session scoren
                    </Button>
                  </div>
                  {voiceRunId && (
                    <p className="text-xs text-muted-foreground">
                      run #{voiceRunId}
                      {voiceSignaling ? ` · ${voiceSignaling}` : ""} — im
                      Workflow-Player verbinden, sprechen, auflegen, dann scoren.
                    </p>
                  )}
                </>
              )}

              {actionMsg && (
                <p className="text-sm text-muted-foreground">{actionMsg}</p>
              )}

              {attempt && (
                <Card className="border-dashed p-3">
                  <div className="flex items-center gap-2">
                    {attempt.passed ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <span className="font-semibold">
                      Score {attempt.score}% —{" "}
                      {attempt.passed ? "bestanden" : "nicht bestanden"}
                    </span>
                  </div>
                  {attemptItems.length > 0 && (
                    <ul className="mt-2 space-y-1 text-xs">
                      {attemptItems.map((it) => (
                        <li key={it.question_id} className="flex gap-2">
                          {it.correct ? (
                            <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5 shrink-0 text-red-500" />
                          )}
                          <span>
                            {it.question_id}
                            {it.explanation ? ` — ${it.explanation}` : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {(attempt.mode === "text" || attempt.mode === "voice") &&
                    attempt.result && (
                    <pre className="mt-2 max-h-40 overflow-auto text-[10px] text-muted-foreground">
                      {JSON.stringify(
                        {
                          disposition: attempt.result.disposition,
                          disposition_success:
                            attempt.result.disposition_success,
                          assertion_pass_rate:
                            attempt.result.assertion_pass_rate,
                          workflow_run_id: attempt.workflow_run_id,
                        },
                        null,
                        2,
                      )}
                    </pre>
                  )}
                </Card>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
