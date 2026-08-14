"use client";

import {
  CheckCircle2,
  FileCode2,
  GitCompare,
  RefreshCw,
  Search,
  Send,
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
import { Textarea } from "@/components/ui/textarea";
import {
  type ApprovalStatus,
  type DefinitionDiffResponse,
  type PromptSearchHit,
  type ScriptEntry,
  createScript,
  diffDefinitions,
  listScripts,
  searchPrompts,
  updateScript,
} from "@/lib/api/scripts";
import { useAuth } from "@/lib/auth";

type WorkflowOption = { id: number; name: string };

const STATUS_OPTIONS: Array<ApprovalStatus | "all"> = [
  "all",
  "draft",
  "pending",
  "approved",
  "rejected",
];

export default function ScriptsLibraryPage() {
  const auth = useAuth();
  const [items, setItems] = useState<ScriptEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [tagFilter, setTagFilter] = useState("");
  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);

  // create form
  const [newTitle, setNewTitle] = useState("");
  const [newWorkflow, setNewWorkflow] = useState("");
  const [newTags, setNewTags] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  // prompt search
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<PromptSearchHit[]>([]);
  const [searching, setSearching] = useState(false);

  // diff
  const [defA, setDefA] = useState("");
  const [defB, setDefB] = useState("");
  const [diff, setDiff] = useState<DefinitionDiffResponse | null>(null);
  const [diffing, setDiffing] = useState(false);

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
    try {
      const res = await listScripts({
        approval_status: statusFilter === "all" ? undefined : statusFilter,
        tag: tagFilter.trim() || undefined,
        limit: 100,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [auth.isAuthenticated, statusFilter, tagFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const onCreate = async () => {
    if (!newTitle.trim() || !newWorkflow) return;
    setCreating(true);
    setError(null);
    try {
      await createScript({
        workflow_id: Number(newWorkflow),
        title: newTitle.trim(),
        description: newDesc,
        tags: newTags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setNewTitle("");
      setNewDesc("");
      setNewTags("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const setStatus = async (id: number, approval_status: ApprovalStatus) => {
    try {
      await updateScript(id, { approval_status });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  };

  const onSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const res = await searchPrompts(query.trim());
      setHits(res.hits);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const onDiff = async () => {
    const a = Number(defA);
    const b = Number(defB);
    if (!a || !b) return;
    setDiffing(true);
    setError(null);
    try {
      setDiff(await diffDefinitions(a, b));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Diff failed");
      setDiff(null);
    } finally {
      setDiffing(false);
    }
  };

  const pending = items.filter((i) => i.approval_status === "pending");

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 md:p-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <FileCode2 className="h-6 w-6" />
            Script Library
          </h1>
          <p className="text-sm text-muted-foreground">
            Tags, Owner, Freigabe-Queue · Prompt-Suche (Postgres FTS) ·
            Version-Diff.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Aktualisieren
        </Button>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="space-y-3 p-4 lg:col-span-1">
          <h2 className="text-sm font-medium">Neuer Eintrag</h2>
          <div className="space-y-1.5">
            <Label>Titel</Label>
            <Input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Discovery Script v3"
            />
          </div>
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
          <div className="space-y-1.5">
            <Label>Tags (kommagetrennt)</Label>
            <Input
              value={newTags}
              onChange={(e) => setNewTags(e.target.value)}
              placeholder="sales, de, outbound"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Beschreibung</Label>
            <Textarea
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              rows={3}
            />
          </div>
          <Button onClick={onCreate} disabled={creating || !newTitle || !newWorkflow}>
            Anlegen
          </Button>
        </Card>

        <Card className="space-y-3 p-4 lg:col-span-2">
          <h2 className="flex items-center gap-2 text-sm font-medium">
            <Search className="h-4 w-4" />
            Prompt-Suche (FTS)
          </h2>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="z.B. budget objection, voicemail…"
              onKeyDown={(e) => e.key === "Enter" && onSearch()}
            />
            <Button onClick={onSearch} disabled={searching}>
              Suchen
            </Button>
          </div>
          <ul className="max-h-64 space-y-2 overflow-y-auto">
            {hits.length === 0 && (
              <li className="text-sm text-muted-foreground">
                Keine Treffer — Query eingeben und suchen.
              </li>
            )}
            {hits.map((h, i) => (
              <li
                key={`${h.definition_id}-${h.node_id}-${i}`}
                className="rounded-lg border bg-muted/20 p-2 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">
                    {h.workflow_name}
                  </span>
                  <span>def #{h.definition_id}</span>
                  <span>
                    {h.node_name} · {h.node_type}
                  </span>
                  {h.version_number != null && (
                    <Badge variant="secondary">v{h.version_number}</Badge>
                  )}
                </div>
                <p className="mt-1 text-xs leading-relaxed">{h.prompt_excerpt}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="space-y-3 p-4">
        <h2 className="flex items-center gap-2 text-sm font-medium">
          <GitCompare className="h-4 w-4" />
          Version-Diff (definition_ids)
        </h2>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="space-y-1.5">
            <Label>Definition A</Label>
            <Input
              value={defA}
              onChange={(e) => setDefA(e.target.value)}
              placeholder="z.B. 12"
              inputMode="numeric"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Definition B</Label>
            <Input
              value={defB}
              onChange={(e) => setDefB(e.target.value)}
              placeholder="z.B. 15"
              inputMode="numeric"
            />
          </div>
          <Button onClick={onDiff} disabled={diffing}>
            Diff
          </Button>
        </div>
        {diff && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              +{diff.summary.added || 0} / −{diff.summary.removed || 0} / ~
              {diff.summary.changed || 0} Änderungen
            </p>
            <ul className="max-h-72 space-y-2 overflow-y-auto">
              {diff.changes.length === 0 && (
                <li className="text-sm text-muted-foreground">
                  Keine Prompt-Unterschiede.
                </li>
              )}
              {diff.changes.map((c, i) => (
                <li
                  key={`${c.node_id}-${c.field}-${i}`}
                  className="rounded border p-2 text-xs"
                >
                  <div className="mb-1 font-medium">
                    [{c.change}] {c.node_name} · {c.field}
                  </div>
                  {c.before && (
                    <pre className="mb-1 whitespace-pre-wrap rounded bg-red-500/10 p-1 text-[11px] text-red-800 dark:text-red-200">
                      − {c.before.slice(0, 400)}
                    </pre>
                  )}
                  {c.after && (
                    <pre className="whitespace-pre-wrap rounded bg-emerald-500/10 p-1 text-[11px] text-emerald-800 dark:text-emerald-200">
                      + {c.after.slice(0, 400)}
                    </pre>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {pending.length > 0 && (
        <Card className="border-amber-500/30 bg-amber-500/5 p-4">
          <h2 className="mb-2 flex items-center gap-2 text-sm font-medium">
            <Send className="h-4 w-4" />
            Freigabe-Queue ({pending.length})
          </h2>
          <ul className="space-y-2">
            {pending.map((p) => (
              <li
                key={p.id}
                className="flex flex-col gap-2 rounded-lg border bg-background p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="font-medium">{p.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {p.workflow_name} · Owner {p.owner_email || p.owner_user_id}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setStatus(p.id, "approved")}
                  >
                    <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setStatus(p.id, "rejected")}
                  >
                    Reject
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="space-y-1.5">
          <Label>Status-Filter</Label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Tag-Filter</Label>
          <Input
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
            placeholder="sales"
            className="w-[180px]"
          />
        </div>
        <p className="text-xs text-muted-foreground sm:ml-auto">
          {total} Einträge
        </p>
      </div>

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {items.length === 0 && (
            <Card className="col-span-full p-8 text-center text-sm text-muted-foreground">
              Noch keine Script-Einträge. Lege oben einen an.
            </Card>
          )}
          {items.map((item) => (
            <Card key={item.id} className="flex flex-col gap-2 p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-medium leading-tight">{item.title}</h3>
                  <p className="text-xs text-muted-foreground">
                    {item.workflow_name || `Workflow ${item.workflow_id}`}
                    {item.definition_id ? ` · def #${item.definition_id}` : ""}
                  </p>
                </div>
                <Badge
                  variant={
                    item.approval_status === "approved"
                      ? "default"
                      : item.approval_status === "pending"
                        ? "secondary"
                        : "outline"
                  }
                >
                  {item.approval_status}
                </Badge>
              </div>
              {item.description && (
                <p className="line-clamp-2 text-xs text-muted-foreground">
                  {item.description}
                </p>
              )}
              <div className="flex flex-wrap gap-1">
                {(item.tags || []).map((t) => (
                  <span
                    key={t}
                    className="rounded bg-muted px-1.5 py-0.5 text-[11px]"
                  >
                    {t}
                  </span>
                ))}
              </div>
              <div className="mt-auto flex flex-wrap gap-2 pt-2">
                {item.approval_status === "draft" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setStatus(item.id, "pending")}
                  >
                    Zur Freigabe
                  </Button>
                )}
                {item.approval_status === "pending" && (
                  <>
                    <Button
                      size="sm"
                      onClick={() => setStatus(item.id, "approved")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setStatus(item.id, "rejected")}
                    >
                      Reject
                    </Button>
                  </>
                )}
                <span className="ml-auto self-center text-[11px] text-muted-foreground">
                  Owner {item.owner_email || `#${item.owner_user_id}`}
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
