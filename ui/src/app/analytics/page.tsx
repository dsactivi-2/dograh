"use client";

import { format, subDays } from "date-fns";
import { BarChart3, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

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
import { Skeleton } from "@/components/ui/skeleton";
import {
  type OutcomeRunRow,
  type OutcomesSummary,
  fetchOutcomesRuns,
  fetchOutcomesSummary,
} from "@/lib/api/outcomes";
import {
  type OrgDispositionSummaryItem,
  fetchOrgDispositionSummary,
  fetchWorkflowTaxonomy,
  saveWorkflowTaxonomy,
  type DispositionTaxonomy,
} from "@/lib/api/disposition";
import { useAuth } from "@/lib/auth";

type WorkflowOption = { id: number; name: string };

export default function AnalyticsOutcomesPage() {
  const auth = useAuth();
  const [fromDate, setFromDate] = useState(
    format(subDays(new Date(), 6), "yyyy-MM-dd"),
  );
  const [toDate, setToDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [timezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [workflowId, setWorkflowId] = useState<string>("all");
  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);
  const [summary, setSummary] = useState<OutcomesSummary | null>(null);
  const [runs, setRuns] = useState<OutcomeRunRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [orgCodes, setOrgCodes] = useState<OrgDispositionSummaryItem[]>([]);
  const [taxDraft, setTaxDraft] = useState<DispositionTaxonomy | null>(null);
  const [taxSaving, setTaxSaving] = useState(false);
  const [taxMsg, setTaxMsg] = useState<string | null>(null);

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
      try {
        setOrgCodes(await fetchOrgDispositionSummary());
      } catch {
        /* optional panel */
      }
    })();
  }, [auth.isAuthenticated]);

  useEffect(() => {
    if (!auth.isAuthenticated || workflowId === "all") {
      setTaxDraft(null);
      return;
    }
    (async () => {
      try {
        const res = await fetchWorkflowTaxonomy(Number(workflowId));
        setTaxDraft(res.taxonomy);
        setTaxMsg(null);
      } catch (e) {
        setTaxMsg(e instanceof Error ? e.message : "Taxonomy load failed");
      }
    })();
  }, [auth.isAuthenticated, workflowId]);

  const load = useCallback(async () => {
    if (!auth.isAuthenticated) return;
    setLoading(true);
    setError(null);
    const wf =
      workflowId !== "all" ? Number(workflowId) : null;
    try {
      const [sum, list] = await Promise.all([
        fetchOutcomesSummary({
          from_date: fromDate,
          to_date: toDate,
          timezone,
          workflow_id: wf,
        }),
        fetchOutcomesRuns({
          from_date: fromDate,
          to_date: toDate,
          timezone,
          workflow_id: wf,
          page: 1,
          limit: 50,
        }),
      ]);
      setSummary(sum);
      setRuns(list.runs || []);
      setTotal(list.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load outcomes");
      setSummary(null);
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, [auth.isAuthenticated, fromDate, toDate, timezone, workflowId]);

  useEffect(() => {
    load();
  }, [load]);

  const saveTaxonomy = async () => {
    if (!taxDraft || workflowId === "all") return;
    setTaxSaving(true);
    setTaxMsg(null);
    try {
      const res = await saveWorkflowTaxonomy(Number(workflowId), taxDraft);
      setTaxDraft(res.taxonomy);
      setTaxMsg("Taxonomy gespeichert");
      setOrgCodes(await fetchOrgDispositionSummary());
    } catch (e) {
      setTaxMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setTaxSaving(false);
    }
  };

  const toggleSuccess = (code: string) => {
    if (!taxDraft) return;
    const set = new Set(taxDraft.success_codes);
    if (set.has(code)) set.delete(code);
    else set.add(code);
    const success_codes = Array.from(set);
    const code_meta = { ...taxDraft.code_meta };
    for (const c of taxDraft.disposition_codes) {
      const prev = code_meta[c] || {
        label: c,
        category: "other" as const,
        description: "",
      };
      code_meta[c] = {
        ...prev,
        category: success_codes.includes(c) ? "success" : prev.category === "success" ? "other" : prev.category,
      };
    }
    setTaxDraft({ ...taxDraft, success_codes, code_meta });
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 md:p-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <BarChart3 className="h-6 w-6" />
            Outcomes Analytics
          </h1>
          <p className="text-sm text-muted-foreground">
            Disposition-Verteilung, QA-Coverage (Schema v1) und Success-Set pro
            Workflow — typisierte Outcomes-API.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Aktualisieren
        </Button>
      </div>

      <Card className="grid gap-4 p-4 md:grid-cols-4">
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
        <div className="space-y-1.5 md:col-span-2">
          <Label>Workflow</Label>
          <Select value={workflowId} onValueChange={setWorkflowId}>
            <SelectTrigger>
              <SelectValue placeholder="Alle Workflows" />
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
      </Card>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </Card>
      )}

      {loading && !summary ? (
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Runs gesamt" value={summary.total_runs} />
            <MetricCard label="Abgeschlossen" value={summary.completed_runs} />
            <MetricCard
              label="QA Coverage"
              value={`${summary.qa_coverage.coverage_pct}%`}
              hint={`${summary.qa_coverage.runs_with_qa} mit QA`}
            />
            <MetricCard
              label="Ø QA Score"
              value={
                summary.average_qa_score != null
                  ? summary.average_qa_score.toFixed(1)
                  : "—"
              }
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-4">
              <h2 className="mb-3 text-sm font-medium text-muted-foreground">
                Dispositionen
              </h2>
              <ul className="space-y-2">
                {summary.disposition_distribution.length === 0 && (
                  <li className="text-sm text-muted-foreground">Keine Daten</li>
                )}
                {summary.disposition_distribution.map((d) => (
                  <li
                    key={d.disposition}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span className="font-medium">{d.disposition}</span>
                    <span className="text-muted-foreground">
                      {d.count} ({d.percentage}%)
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card className="p-4">
              <h2 className="mb-3 text-sm font-medium text-muted-foreground">
                Top QA-Tags
              </h2>
              <ul className="space-y-2">
                {summary.top_qa_tags.length === 0 && (
                  <li className="text-sm text-muted-foreground">
                    Noch keine QA-Tags im Zeitraum
                  </li>
                )}
                {summary.top_qa_tags.map((t) => (
                  <li
                    key={t.tag}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                      {t.tag}
                    </span>
                    <span className="text-muted-foreground">{t.count}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      ) : null}

      {workflowId !== "all" && taxDraft && (
        <Card className="p-4">
          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-medium">Disposition Taxonomy</h2>
              <p className="text-xs text-muted-foreground">
                Success-Set markieren — speist Outcomes/Analytics.
              </p>
            </div>
            <Button size="sm" onClick={saveTaxonomy} disabled={taxSaving}>
              {taxSaving ? "Speichern…" : "Taxonomy speichern"}
            </Button>
          </div>
          {taxMsg && (
            <p className="mb-2 text-xs text-muted-foreground">{taxMsg}</p>
          )}
          <div className="flex flex-wrap gap-2">
            {taxDraft.disposition_codes.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Noch keine Codes am Workflow. Codes entstehen bei Calls oder
                im Workflow-Editor.
              </p>
            )}
            {taxDraft.disposition_codes.map((code) => {
              const isSuccess = taxDraft.success_codes.includes(code);
              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => toggleSuccess(code)}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                    isSuccess
                      ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                      : "border-border bg-muted/40 text-foreground"
                  }`}
                >
                  {code}
                  {isSuccess ? " · success" : ""}
                </button>
              );
            })}
          </div>
        </Card>
      )}

      {orgCodes.length > 0 && (
        <Card className="p-4">
          <h2 className="mb-2 text-sm font-medium text-muted-foreground">
            Org-weite Disposition-Codes
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {orgCodes.map((c) => (
              <span
                key={c.code}
                className={`rounded-md px-2 py-0.5 text-[11px] ${
                  c.is_success
                    ? "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200"
                    : "bg-muted"
                }`}
                title={`${c.label} · ${c.workflow_count} workflows`}
              >
                {c.code}
                {c.is_success ? " ★" : ""}
              </span>
            ))}
          </div>
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="border-b px-4 py-3">
          <h2 className="text-sm font-medium">
            Runs {total > 0 ? `(${Math.min(runs.length, total)} / ${total})` : ""}
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Run</th>
                <th className="px-3 py-2 font-medium">Disposition</th>
                <th className="px-3 py-2 font-medium">Dauer</th>
                <th className="px-3 py-2 font-medium">QA</th>
                <th className="px-3 py-2 font-medium">Tags</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 && !loading && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-8 text-center text-muted-foreground"
                  >
                    Keine Runs im gewählten Zeitraum.
                  </td>
                </tr>
              )}
              {runs.map((r) => (
                <tr key={r.run_id} className="border-t">
                  <td className="px-3 py-2">
                    <div className="font-medium">#{r.run_id}</div>
                    <div className="text-xs text-muted-foreground">
                      {r.workflow_name || `Workflow ${r.workflow_id}`}
                      {r.phone_number ? ` · ${r.phone_number}` : ""}
                    </div>
                  </td>
                  <td className="px-3 py-2 font-medium">{r.disposition}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {r.duration_seconds != null
                      ? `${Math.round(r.duration_seconds)}s`
                      : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {r.qa?.has_qa
                      ? r.qa.overall_score != null
                        ? r.qa.overall_score.toFixed(0)
                        : "yes"
                      : "—"}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {(r.qa?.tags || r.call_tags || []).slice(0, 4).map((t) => (
                        <span
                          key={t}
                          className="rounded bg-muted px-1.5 py-0.5 text-[11px]"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint ? (
        <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>
      ) : null}
    </Card>
  );
}
