"use client";

import { format, subDays } from "date-fns";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  RefreshCw,
  RotateCcw,
  Save,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  type QaCenterRunRow,
  type QaCenterSummary,
  fetchQaCenterQueue,
  fetchQaCenterSummary,
  rerunQa,
  saveQaOverride,
} from "@/lib/api/qaCenter";
import { useAuth } from "@/lib/auth";

type WorkflowOption = { id: number; name: string };

function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-muted-foreground";
  if (score <= 3) return "text-red-600 dark:text-red-400";
  if (score <= 6) return "text-amber-600 dark:text-amber-400";
  return "text-emerald-600 dark:text-emerald-400";
}

function FlagBadge({ status }: { status: string }) {
  if (status === "pass") {
    return (
      <Badge variant="outline" className="gap-1 border-emerald-500/40 text-emerald-700 dark:text-emerald-400">
        <CheckCircle2 className="h-3 w-3" /> pass
      </Badge>
    );
  }
  if (status === "fail") {
    return (
      <Badge variant="outline" className="gap-1 border-red-500/40 text-red-700 dark:text-red-400">
        <XCircle className="h-3 w-3" /> fail
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1 text-muted-foreground">
      ?
    </Badge>
  );
}

export default function QaCenterPage() {
  const auth = useAuth();
  const [fromDate, setFromDate] = useState(
    format(subDays(new Date(), 6), "yyyy-MM-dd"),
  );
  const [toDate, setToDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [timezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [workflowId, setWorkflowId] = useState<string>("all");
  const [maxScore, setMaxScore] = useState("6");
  const [onlyReview, setOnlyReview] = useState(true);
  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);
  const [summary, setSummary] = useState<QaCenterSummary | null>(null);
  const [runs, setRuns] = useState<QaCenterRunRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<QaCenterRunRow | null>(null);
  const [ovScore, setOvScore] = useState("");
  const [ovSentiment, setOvSentiment] = useState("");
  const [ovTags, setOvTags] = useState("");
  const [ovSummary, setOvSummary] = useState("");
  const [ovNotes, setOvNotes] = useState("");
  const [ovIdentity, setOvIdentity] = useState<string>("unknown");
  const [ovDisclosure, setOvDisclosure] = useState<string>("unknown");
  const [saving, setSaving] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

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

  const load = useCallback(async () => {
    if (!auth.isAuthenticated) return;
    setLoading(true);
    setError(null);
    const wf = workflowId !== "all" ? Number(workflowId) : null;
    const thr = Number(maxScore) || 6;
    try {
      const [sum, queue] = await Promise.all([
        fetchQaCenterSummary({
          from_date: fromDate,
          to_date: toDate,
          timezone,
          workflow_id: wf,
          max_score: thr,
        }),
        fetchQaCenterQueue({
          from_date: fromDate,
          to_date: toDate,
          timezone,
          workflow_id: wf,
          max_score: thr,
          only_needs_review: onlyReview,
          page: 1,
          limit: 50,
        }),
      ]);
      setSummary(sum);
      setRuns(queue.runs || []);
      setTotal(queue.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load QA Center");
      setSummary(null);
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, [
    auth.isAuthenticated,
    fromDate,
    toDate,
    timezone,
    workflowId,
    maxScore,
    onlyReview,
  ]);

  useEffect(() => {
    load();
  }, [load]);

  const openRun = (row: QaCenterRunRow) => {
    setSelected(row);
    setActionMsg(null);
    setOvScore(
      row.effective_score != null ? String(row.effective_score) : "",
    );
    setOvSentiment(row.effective_sentiment || "");
    setOvTags(row.effective_tags.join(", "));
    setOvSummary(row.effective_summary || "");
    setOvNotes(row.override?.notes || "");
    const idFlag = row.compliance_flags.find((f) => f.key === "identity_verified");
    const discFlag = row.compliance_flags.find((f) => f.key === "disclosure_made");
    setOvIdentity(idFlag?.status === "pass" ? "pass" : idFlag?.status === "fail" ? "fail" : "unknown");
    setOvDisclosure(
      discFlag?.status === "pass"
        ? "pass"
        : discFlag?.status === "fail"
          ? "fail"
          : "unknown",
    );
  };

  const flagToBool = (v: string): boolean | null => {
    if (v === "pass") return true;
    if (v === "fail") return false;
    return null;
  };

  const saveOverride = async () => {
    if (!selected) return;
    setSaving(true);
    setActionMsg(null);
    try {
      const scoreNum = ovScore.trim() === "" ? null : Number(ovScore);
      const res = await saveQaOverride(selected.run_id, {
        overall_score: scoreNum != null && !Number.isNaN(scoreNum) ? scoreNum : null,
        sentiment: ovSentiment.trim() || null,
        tags: ovTags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        summary: ovSummary,
        notes: ovNotes,
        compliance_flags: {
          identity_verified: flagToBool(ovIdentity),
          disclosure_made: flagToBool(ovDisclosure),
        },
      });
      setSelected(res.run);
      setActionMsg("Override gespeichert (Audit-Trail in annotations)");
      await load();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const doRerun = async () => {
    if (!selected) return;
    setRerunning(true);
    setActionMsg(null);
    try {
      const res = await rerunQa(selected.run_id);
      setActionMsg(
        res.status === "queued"
          ? "QA Re-Run in ARQ-Queue"
          : `Re-Run nicht möglich: ${res.message}`,
      );
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Re-run failed");
    } finally {
      setRerunning(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 md:p-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <ClipboardCheck className="h-6 w-6" />
            QA Center
          </h1>
          <p className="text-sm text-muted-foreground">
            Review-Queue für Low-Score, Problem-Tags und Compliance — Schema-v1
            QA + manuelles Override mit Audit.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw
            className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          Aktualisieren
        </Button>
      </div>

      <Card className="grid gap-4 p-4 md:grid-cols-5">
        <div className="space-y-1.5">
          <Label htmlFor="from">Von</Label>
          <Input
            id="from"
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="to">Bis</Label>
          <Input
            id="to"
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Workflow</Label>
          <Select value={workflowId} onValueChange={setWorkflowId}>
            <SelectTrigger>
              <SelectValue placeholder="Alle" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Alle Workflows</SelectItem>
              {workflows.map((w) => (
                <SelectItem key={w.id} value={String(w.id)}>
                  {w.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="maxScore">Low-Score ≤</Label>
          <Input
            id="maxScore"
            type="number"
            min={0}
            max={100}
            step={0.5}
            value={maxScore}
            onChange={(e) => setMaxScore(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Queue-Filter</Label>
          <Select
            value={onlyReview ? "review" : "all"}
            onValueChange={(v) => setOnlyReview(v === "review")}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="review">Nur Review nötig</SelectItem>
              <SelectItem value="all">Alle Runs im Zeitraum</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </Card>
      )}

      {loading && !summary ? (
        <div className="grid gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : summary ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                QA Coverage
              </p>
              <p className="mt-1 text-2xl font-semibold">
                {summary.coverage_pct.toFixed(1)}%
              </p>
              <p className="text-xs text-muted-foreground">
                {summary.runs_with_qa}/{summary.total_runs} Runs
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Ø Score
              </p>
              <p
                className={`mt-1 text-2xl font-semibold ${scoreColor(summary.average_score)}`}
              >
                {summary.average_score != null
                  ? summary.average_score.toFixed(1)
                  : "—"}
              </p>
              <p className="text-xs text-muted-foreground">
                Low-Score: {summary.low_score_count}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Review Queue
              </p>
              <p className="mt-1 flex items-center gap-2 text-2xl font-semibold">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                {summary.needs_review_count}
              </p>
              <p className="text-xs text-muted-foreground">
                Problem-Tags: {summary.problem_tag_count} · Overrides:{" "}
                {summary.override_count}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Compliance Fails
              </p>
              <p className="mt-1 flex items-center gap-2 text-2xl font-semibold text-red-600 dark:text-red-400">
                <ShieldAlert className="h-5 w-5" />
                {summary.compliance_fail_runs}
              </p>
              <p className="text-xs text-muted-foreground">
                Runs mit mind. einem Fail-Flag
              </p>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-4">
              <h2 className="mb-3 text-sm font-semibold">Sentiment</h2>
              <div className="flex flex-wrap gap-2">
                {summary.sentiment_distribution.map((s) => (
                  <Badge key={s.sentiment} variant="secondary">
                    {s.sentiment}: {s.count} ({s.percentage}%)
                  </Badge>
                ))}
                {summary.sentiment_distribution.length === 0 && (
                  <p className="text-sm text-muted-foreground">Keine Daten</p>
                )}
              </div>
              <h2 className="mb-2 mt-4 text-sm font-semibold">Score-Buckets</h2>
              <div className="flex flex-wrap gap-2">
                {summary.score_distribution.map((b) => (
                  <Badge key={b.bucket} variant="outline">
                    {b.bucket}: {b.count}
                  </Badge>
                ))}
              </div>
            </Card>
            <Card className="p-4">
              <h2 className="mb-3 text-sm font-semibold">Top Tags</h2>
              <div className="flex flex-wrap gap-2">
                {summary.top_tags.slice(0, 15).map((t) => (
                  <Badge key={t.tag} variant="secondary">
                    {t.tag} · {t.count}
                  </Badge>
                ))}
                {summary.top_tags.length === 0 && (
                  <p className="text-sm text-muted-foreground">Keine Tags</p>
                )}
              </div>
              <h2 className="mb-2 mt-4 text-sm font-semibold">
                Compliance Übersicht
              </h2>
              <div className="space-y-1.5">
                {summary.compliance_summary.map((c) => (
                  <div
                    key={c.key}
                    className="flex items-center justify-between gap-2 text-xs"
                  >
                    <span className="font-medium">{c.label}</span>
                    <span className="text-muted-foreground">
                      ✓{c.pass_count} · ✗{c.fail_count} · ?{c.unknown_count}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="overflow-hidden lg:col-span-3">
          <div className="border-b px-4 py-3">
            <h2 className="text-sm font-semibold">
              {onlyReview ? "Review Queue" : "Runs"} ({total})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Run</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Sentiment</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Compliance</TableHead>
                  <TableHead>Reasons</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && runs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Skeleton className="h-8 w-full" />
                    </TableCell>
                  </TableRow>
                ) : runs.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="py-8 text-center text-sm text-muted-foreground"
                    >
                      Keine Einträge im Zeitraum.
                    </TableCell>
                  </TableRow>
                ) : (
                  runs.map((r) => (
                    <TableRow
                      key={r.run_id}
                      className={`cursor-pointer ${selected?.run_id === r.run_id ? "bg-muted/60" : ""}`}
                      onClick={() => openRun(r)}
                    >
                      <TableCell className="whitespace-nowrap text-sm">
                        <div className="font-medium">#{r.run_id}</div>
                        <div className="text-xs text-muted-foreground">
                          {r.workflow_name || `wf ${r.workflow_id}`}
                        </div>
                        {r.has_override && (
                          <Badge variant="outline" className="mt-1 text-[10px]">
                            override
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell
                        className={`font-semibold ${scoreColor(r.effective_score)}`}
                      >
                        {r.effective_score != null
                          ? r.effective_score.toFixed(1)
                          : "—"}
                      </TableCell>
                      <TableCell className="text-sm capitalize">
                        {r.effective_sentiment || "—"}
                      </TableCell>
                      <TableCell>
                        <div className="flex max-w-[160px] flex-wrap gap-1">
                          {r.effective_tags.slice(0, 3).map((t) => (
                            <Badge
                              key={t}
                              variant="secondary"
                              className="text-[10px]"
                            >
                              {t}
                            </Badge>
                          ))}
                          {r.effective_tags.length > 3 && (
                            <span className="text-[10px] text-muted-foreground">
                              +{r.effective_tags.length - 3}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {r.compliance_fail_count > 0 ? (
                          <Badge variant="destructive" className="text-[10px]">
                            {r.compliance_fail_count} fail
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">ok</span>
                        )}
                      </TableCell>
                      <TableCell className="max-w-[140px] truncate text-xs text-muted-foreground">
                        {r.review_reasons.join(" · ") || "—"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </Card>

        <Card className="p-4 lg:col-span-2">
          {!selected ? (
            <div className="flex h-full min-h-[280px] items-center justify-center text-sm text-muted-foreground">
              Run in der Queue wählen für Detail + Override
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div>
                <h2 className="text-sm font-semibold">
                  Run #{selected.run_id}
                </h2>
                <p className="text-xs text-muted-foreground">
                  {selected.workflow_name} · {selected.disposition} ·{" "}
                  {selected.phone_number || "no phone"}
                </p>
                {selected.effective_summary && (
                  <p className="mt-2 text-sm">{selected.effective_summary}</p>
                )}
              </div>

              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Compliance
                </h3>
                <div className="space-y-1">
                  {selected.compliance_flags.map((f) => (
                    <div
                      key={f.key}
                      className="flex items-center justify-between gap-2 text-xs"
                    >
                      <span>{f.label}</span>
                      <FlagBadge status={f.status} />
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2 border-t pt-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Manuelles Override
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Score (1–10)</Label>
                    <Input
                      value={ovScore}
                      onChange={(e) => setOvScore(e.target.value)}
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Sentiment</Label>
                    <Select value={ovSentiment || "neutral"} onValueChange={setOvSentiment}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="positive">positive</SelectItem>
                        <SelectItem value="neutral">neutral</SelectItem>
                        <SelectItem value="negative">negative</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Tags (kommagetrennt)</Label>
                  <Input
                    value={ovTags}
                    onChange={(e) => setOvTags(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Summary</Label>
                  <Textarea
                    value={ovSummary}
                    onChange={(e) => setOvSummary(e.target.value)}
                    rows={2}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Reviewer-Notizen</Label>
                  <Textarea
                    value={ovNotes}
                    onChange={(e) => setOvNotes(e.target.value)}
                    rows={2}
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Identity verified</Label>
                    <Select value={ovIdentity} onValueChange={setOvIdentity}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pass">pass</SelectItem>
                        <SelectItem value="fail">fail</SelectItem>
                        <SelectItem value="unknown">unknown</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Disclosure made</Label>
                    <Select
                      value={ovDisclosure}
                      onValueChange={setOvDisclosure}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pass">pass</SelectItem>
                        <SelectItem value="fail">fail</SelectItem>
                        <SelectItem value="unknown">unknown</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button size="sm" onClick={saveOverride} disabled={saving}>
                    <Save className="mr-1.5 h-3.5 w-3.5" />
                    {saving ? "Speichern…" : "Override speichern"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={doRerun}
                    disabled={rerunning}
                  >
                    <RotateCcw
                      className={`mr-1.5 h-3.5 w-3.5 ${rerunning ? "animate-spin" : ""}`}
                    />
                    QA Re-Run
                  </Button>
                </div>
                {actionMsg && (
                  <p className="text-xs text-muted-foreground">{actionMsg}</p>
                )}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
