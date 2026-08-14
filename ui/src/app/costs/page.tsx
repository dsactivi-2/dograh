"use client";

import { format, subDays } from "date-fns";
import { CircleDollarSign, RefreshCw } from "lucide-react";
import Link from "next/link";
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
import {
  type CostAttributionSummary,
  type CostGroupBy,
  fetchCostAttributionSummary,
} from "@/lib/api/costAttribution";
import { useAuth } from "@/lib/auth";

type WorkflowOption = { id: number; name: string };

function fmtUsd(v: number | null | undefined): string {
  if (v == null) return "—";
  return `$${v.toFixed(4)}`;
}

function fmtDuration(sec: number): string {
  if (!sec) return "0s";
  if (sec < 60) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}m ${s}s`;
}

export default function CostAttributionPage() {
  const auth = useAuth();
  const [fromDate, setFromDate] = useState(
    format(subDays(new Date(), 13), "yyyy-MM-dd"),
  );
  const [toDate, setToDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [timezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [workflowId, setWorkflowId] = useState<string>("all");
  const [campaignIdFilter, setCampaignIdFilter] = useState("");
  const [groupBy, setGroupBy] = useState<CostGroupBy>("workflow");
  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);
  const [summary, setSummary] = useState<CostAttributionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    const cid = campaignIdFilter.trim()
      ? Number(campaignIdFilter.trim())
      : null;
    if (cid != null && Number.isNaN(cid)) {
      setError("campaign_id muss eine Zahl sein");
      setLoading(false);
      return;
    }
    try {
      const data = await fetchCostAttributionSummary({
        from_date: fromDate,
        to_date: toDate,
        timezone,
        workflow_id: wf,
        campaign_id: cid,
        group_by: groupBy,
      });
      setSummary(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cost attribution load failed");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [
    auth.isAuthenticated,
    fromDate,
    toDate,
    timezone,
    workflowId,
    campaignIdFilter,
    groupBy,
  ]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 md:p-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <CircleDollarSign className="h-6 w-6" />
            Cost Attribution
          </h1>
          <p className="text-sm text-muted-foreground">
            Kosten pro Workflow / Campaign / Definition aus{" "}
            <code className="text-xs">cost_info</code> /{" "}
            <code className="text-xs">usage_info</code> — defensiv bei lückenhaften
            Daten, kein neues Billing.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/usage">Agent Runs</Link>
          </Button>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw
              className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            Aktualisieren
          </Button>
        </div>
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
          <Label htmlFor="cid">Campaign ID</Label>
          <Input
            id="cid"
            inputMode="numeric"
            placeholder="optional"
            value={campaignIdFilter}
            onChange={(e) => setCampaignIdFilter(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Group by</Label>
          <Select
            value={groupBy}
            onValueChange={(v) => setGroupBy(v as CostGroupBy)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="workflow">Workflow</SelectItem>
              <SelectItem value="campaign">Campaign</SelectItem>
              <SelectItem value="definition">Definition</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </Card>
      )}

      {loading && !summary ? (
        <div className="grid gap-4 md:grid-cols-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Runs
              </p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">
                {summary.total_runs}
              </p>
              <p className="text-xs text-muted-foreground">
                coverage {summary.cost_coverage_pct}%
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Total cost (USD)
              </p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">
                {fmtUsd(summary.total_cost_usd)}
              </p>
              <p className="text-xs text-muted-foreground">
                charge {fmtUsd(summary.total_charge_usd)}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Duration
              </p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">
                {fmtDuration(summary.total_duration_seconds)}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Dograh tokens
              </p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">
                {summary.total_dograh_tokens.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">
                missing cost: {summary.runs_missing_cost}
              </p>
            </Card>
          </div>

          {summary.notes.length > 0 && (
            <Card className="space-y-1 border-amber-500/30 bg-amber-500/5 p-4 text-sm">
              {summary.notes.map((n) => (
                <p key={n}>{n}</p>
              ))}
            </Card>
          )}

          <Card className="overflow-hidden">
            <div className="border-b px-4 py-3">
              <h2 className="text-sm font-semibold">
                Attribution by {groupBy}
              </h2>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Bucket</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Runs</TableHead>
                    <TableHead className="text-right">With cost</TableHead>
                    <TableHead className="text-right">Cost USD</TableHead>
                    <TableHead className="text-right">Avg USD</TableHead>
                    <TableHead className="text-right">Duration</TableHead>
                    <TableHead className="text-right">Tokens</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {summary.buckets.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={8}
                        className="text-center text-muted-foreground"
                      >
                        Keine Runs im Zeitraum.
                      </TableCell>
                    </TableRow>
                  ) : (
                    summary.buckets.map((b) => (
                      <TableRow key={b.key}>
                        <TableCell className="font-medium">{b.label}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{b.group_type}</Badge>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {b.run_count}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {b.runs_with_cost}
                          <span className="text-muted-foreground">
                            {" "}
                            ({b.cost_coverage_pct}%)
                          </span>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {fmtUsd(b.total_cost_usd)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {fmtUsd(b.avg_cost_usd)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {fmtDuration(b.total_duration_seconds)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {b.total_dograh_tokens.toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}
