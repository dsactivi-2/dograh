"use client";

import { format, subDays } from "date-fns";
import {
  Activity,
  AlertTriangle,
  Megaphone,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
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
  type CampaignOpsRow,
  type CampaignOpsSummary,
  fetchCampaignOpsSummary,
} from "@/lib/api/campaignOps";
import { useAuth } from "@/lib/auth";

type WorkflowOption = { id: number; name: string };

function stateVariant(
  state: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (state) {
    case "running":
      return "default";
    case "paused":
      return "secondary";
    case "failed":
      return "destructive";
    case "completed":
      return "outline";
    default:
      return "secondary";
  }
}

function FunnelBar({
  label,
  count,
  max,
}: {
  label: string;
  count: number;
  max: number;
}) {
  const pct = max > 0 ? Math.min(100, (count / max) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{count}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary/80 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function CampaignControlTowerPage() {
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
  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);
  const [summary, setSummary] = useState<CampaignOpsSummary | null>(null);
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
      const data = await fetchCampaignOpsSummary({
        from_date: fromDate,
        to_date: toDate,
        timezone,
        workflow_id: wf,
        campaign_id: cid,
      });
      setSummary(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Campaign ops load failed");
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
  ]);

  useEffect(() => {
    load();
  }, [load]);

  const maxFunnel =
    summary?.funnel.reduce((m, s) => Math.max(m, s.count), 0) || 1;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 md:p-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <Megaphone className="h-6 w-6" />
            Campaign Control Tower
          </h1>
          <p className="text-sm text-muted-foreground">
            Funnel queued → dialed → connected → disposition, plus Retry- und
            Circuit-Breaker-Sicht — org-scoped über bestehende Campaign-Daten.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/campaigns">Kampagnen</Link>
          </Button>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw
              className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            Aktualisieren
          </Button>
        </div>
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
          <Label htmlFor="cid">Campaign ID (optional)</Label>
          <Input
            id="cid"
            inputMode="numeric"
            placeholder="z.B. 42"
            value={campaignIdFilter}
            onChange={(e) => setCampaignIdFilter(e.target.value)}
          />
        </div>
      </Card>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </Card>
      )}

      {loading && !summary ? (
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Kampagnen
              </p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">
                {summary.campaign_count}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Queued runs
              </p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">
                {summary.totals.queued_runs ?? 0}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Connected
              </p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">
                {summary.totals.runs_connected ?? 0}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Dispositioned
              </p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">
                {summary.totals.dispositioned ?? 0}
              </p>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="space-y-3 p-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Activity className="h-4 w-4" />
                Funnel
              </h2>
              {summary.funnel.map((s) => (
                <FunnelBar
                  key={s.key}
                  label={s.label}
                  count={s.count}
                  max={maxFunnel}
                />
              ))}
            </Card>
            <Card className="space-y-3 p-4">
              <h2 className="text-sm font-semibold">Disposition (org)</h2>
              {summary.disposition_distribution.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Keine Dispositionen im Zeitraum.
                </p>
              ) : (
                <div className="max-h-64 space-y-2 overflow-y-auto">
                  {summary.disposition_distribution.slice(0, 12).map((d) => (
                    <div
                      key={d.disposition}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="truncate font-mono text-xs">
                        {d.disposition}
                      </span>
                      <span className="tabular-nums text-muted-foreground">
                        {d.count} · {d.percentage}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <Card className="overflow-hidden">
            <div className="border-b px-4 py-3">
              <h2 className="text-sm font-semibold">Kampagnen-Detail</h2>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Campaign</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead className="text-right">Queue</TableHead>
                    <TableHead className="text-right">Connected</TableHead>
                    <TableHead>Retry</TableHead>
                    <TableHead>Circuit breaker</TableHead>
                    <TableHead>Top disposition</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {summary.campaigns.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={7}
                        className="text-center text-muted-foreground"
                      >
                        Keine Kampagnen im Filter.
                      </TableCell>
                    </TableRow>
                  ) : (
                    summary.campaigns.map((c: CampaignOpsRow) => {
                      const topDisp =
                        c.disposition_distribution[0]?.disposition || "—";
                      const cb = c.circuit_breaker;
                      return (
                        <TableRow key={c.campaign_id}>
                          <TableCell>
                            <Link
                              href={`/campaigns/${c.campaign_id}`}
                              className="font-medium hover:underline"
                            >
                              {c.campaign_name || `#${c.campaign_id}`}
                            </Link>
                            <div className="text-xs text-muted-foreground">
                              {c.workflow_name} · id {c.campaign_id}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant={stateVariant(c.state)}>
                              {c.state}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right text-xs tabular-nums">
                            <div>
                              {c.queued}q / {c.processing}p / {c.processed}d
                            </div>
                            <div className="text-muted-foreground">
                              fail {c.failed_queued} · total{" "}
                              {c.total_queued_runs}
                            </div>
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {c.runs_connected}/{c.runs_total}
                          </TableCell>
                          <TableCell className="text-xs">
                            {c.retry.enabled ? (
                              <span>
                                on · max {c.retry.max_retries}
                                {c.retry.total_with_retry > 0
                                  ? ` · ${c.retry.total_with_retry} retried`
                                  : ""}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">off</span>
                            )}
                          </TableCell>
                          <TableCell className="text-xs">
                            {!cb.enabled ? (
                              <span className="text-muted-foreground">off</span>
                            ) : cb.is_open ? (
                              <span className="inline-flex items-center gap-1 text-destructive">
                                <ShieldAlert className="h-3.5 w-3.5" />
                                OPEN
                                {cb.failure_rate != null
                                  ? ` ${(cb.failure_rate * 100).toFixed(0)}%`
                                  : ""}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1">
                                {cb.source === "unavailable" ? (
                                  <>
                                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                                    cfg only
                                  </>
                                ) : (
                                  "closed"
                                )}
                                {cb.failure_rate != null
                                  ? ` · ${(cb.failure_rate * 100).toFixed(0)}%`
                                  : ""}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {topDisp}
                          </TableCell>
                        </TableRow>
                      );
                    })
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
