"use client";

import Link from "next/link";
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Select } from "@/components/common/field";
import { StatusBadge } from "@/components/cards/status-badge";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";
import { formatPercent, formatStatus } from "@/utils/utils";
import { useMemo, useState } from "react";
import { toast } from "sonner";

type Alert = {
  id: string;
  child_id: string;
  pseudonymous_id: string;
  type: string;
  severity: string;
  status: string;
  message: string;
  trigger_value?: { previous_risk?: number; current_risk?: number; risk_velocity?: number; basis?: string };
  created_at: string;
};

type InboxTab = "needs-review" | "resolved";

const TAB_STATUSES: Record<InboxTab, readonly string[]> = {
  "needs-review": ["OPEN", "IN_REVIEW", "ACKNOWLEDGED"],
  resolved: ["RESOLVED", "DISMISSED_WITH_REASON"],
};

const SEVERITY_RANK: Record<string, number> = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

/** Source of the alert, in clinician language. Existing alert types only. */
function alertSource(type: string): { label: string; tone: string } {
  if (type === "MISSED_FOLLOW_UP") return { label: "Follow-up schedule", tone: "bg-[#E7EEF6] text-[#14345B]" };
  if (type === "DETERIORATION" || type === "STAGNATION" || type === "RELAPSE") {
    return { label: "12-month prediction change", tone: "bg-[#0E243D] text-white" };
  }
  return { label: "Clinical", tone: "bg-[#F4F7FA] text-[#102A4C]" };
}

export default function AlertsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<InboxTab>("needs-review");
  const [type, setType] = useState("");
  const [dismissId, setDismissId] = useState<string | null>(null);
  const [dismissReason, setDismissReason] = useState("");

  const statuses = TAB_STATUSES[tab];
  const queries = useQueries({
    queries: statuses.map((status) => ({
      queryKey: ["alerts", type, status],
      queryFn: () => api<{ items: Alert[] }>(`/alerts?type=${type}&status=${status}`),
    })),
  });
  const isLoading = queries.some((q) => q.isLoading);
  const errorQuery = queries.find((q) => q.error);
  const items = useMemo(() => {
    const merged = queries.flatMap((q) => q.data?.items ?? []);
    return merged.sort((a, b) => {
      const sev = (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9);
      if (sev !== 0) return sev;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [queries]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["alerts"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["notifications"] });
  };

  const ack = useMutation({
    mutationFn: (id: string) => api(`/alerts/${id}/acknowledge`, { method: "PATCH", body: JSON.stringify({}) }),
    onSuccess: () => {
      toast.success("Alert acknowledged");
      invalidate();
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Unable to update alert"),
  });
  const review = useMutation({
    mutationFn: (id: string) => api(`/alerts/${id}/review`, { method: "PATCH", body: JSON.stringify({}) }),
    onSuccess: () => {
      toast.success("Alert marked in review");
      invalidate();
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Unable to update alert"),
  });
  const resolve = useMutation({
    mutationFn: (id: string) => api(`/alerts/${id}/resolve`, { method: "PATCH", body: JSON.stringify({ notes: "Reviewed in clinic" }) }),
    onSuccess: () => {
      toast.success("Alert resolved");
      invalidate();
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Unable to update alert"),
  });
  const dismiss = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api(`/alerts/${id}/dismiss`, { method: "PATCH", body: JSON.stringify({ reason }) }),
    onSuccess: () => {
      toast.success("Alert dismissed");
      setDismissId(null);
      setDismissReason("");
      invalidate();
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Unable to update alert"),
  });

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-[#102A4C]">Alerts</h1>
        </div>
        <Select className="w-auto min-w-[12.5rem] rounded-xl" value={type} onChange={(e) => setType(e.target.value)} aria-label="Alert type">
          <option value="">All alert types</option>
          <option value="STAGNATION">{formatStatus("STAGNATION")}</option>
          <option value="DETERIORATION">{formatStatus("DETERIORATION")}</option>
          <option value="RELAPSE">{formatStatus("RELAPSE")}</option>
          <option value="MISSED_FOLLOW_UP">{formatStatus("MISSED_FOLLOW_UP")}</option>
        </Select>
      </header>

      <div className="inline-flex rounded-full border border-white/70 bg-white/75 p-1 shadow-card backdrop-blur-xl" role="tablist" aria-label="Inbox">
        {(
          [
            ["needs-review", "Needs review"],
            ["resolved", "Reviewed / resolved"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${tab === id ? "bg-[#102A4C] text-white" : "text-[#5C6E82] hover:text-[#102A4C]"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2" aria-busy="true">
          <Skeleton className="h-48 rounded-[24px]" />
          <Skeleton className="h-48 rounded-[24px]" />
        </div>
      ) : errorQuery?.error ? (
        <ErrorState message={errorQuery.error instanceof Error ? errorQuery.error.message : "Unable to load alerts."} />
      ) : items.length === 0 ? (
        <EmptyState
          title={tab === "needs-review" ? "Nothing waiting for review." : "No reviewed or resolved alerts yet."}
          body={tab === "needs-review" ? "New prediction changes and overdue follow-ups will appear here." : "Resolved and dismissed alerts are kept here for the record."}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((a) => {
            const source = alertSource(a.type);
            return (
              <article key={a.id} className="rounded-[24px] border border-white/70 bg-white/80 p-5 shadow-card backdrop-blur-xl">
                <div className="flex justify-between gap-2">
                  <div className="min-w-0">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${source.tone}`}>{source.label}</span>
                    <p className="mt-2 font-semibold text-[#102A4C]">{a.pseudonymous_id}</p>
                    <p className="text-xs text-[#5C6E82]">
                      {formatStatus(a.type)} · {new Date(a.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <StatusBadge value={a.severity} />
                    <StatusBadge value={a.status} />
                  </div>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-[#102A4C]">{a.message}</p>
                {a.trigger_value?.previous_risk != null && a.trigger_value?.current_risk != null ? (
                  <p className="mt-2 text-sm text-[#5C6E82]">
                    {a.trigger_value?.basis === "predicted_risk_change" ? "Highest predicted condition risk (next 12 months)" : "Model score"}:{" "}
                    {formatPercent(a.trigger_value.previous_risk)} → {formatPercent(a.trigger_value.current_risk)}
                  </p>
                ) : null}
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link href={`/children/${a.child_id}?focus=review`}>
                    <Button variant="secondary">Open child</Button>
                  </Link>
                  {a.status === "OPEN" ? (
                    <>
                      <Button variant="secondary" onClick={() => review.mutate(a.id)} disabled={review.isPending}>
                        Mark in review
                      </Button>
                      <Button onClick={() => ack.mutate(a.id)} disabled={ack.isPending}>
                        Acknowledge
                      </Button>
                    </>
                  ) : null}
                  {a.status === "OPEN" || a.status === "IN_REVIEW" || a.status === "ACKNOWLEDGED" ? (
                    <Button variant="secondary" onClick={() => resolve.mutate(a.id)} disabled={resolve.isPending}>
                      Resolve
                    </Button>
                  ) : null}
                  {a.status !== "DISMISSED_WITH_REASON" && a.status !== "RESOLVED" ? (
                    <Button variant="ghost" onClick={() => setDismissId(a.id)}>
                      Dismiss…
                    </Button>
                  ) : null}
                </div>
                {dismissId === a.id ? (
                  <div className="mt-3 space-y-2 rounded-xl bg-canvas p-3">
                    <input
                      className="w-full rounded-lg border border-line px-3 py-2 text-sm"
                      placeholder="Reason for dismissal (required)"
                      value={dismissReason}
                      onChange={(e) => setDismissReason(e.target.value)}
                      aria-label="Reason for dismissal"
                    />
                    <div className="flex gap-2">
                      <Button
                        className="min-h-9 px-3 text-xs"
                        onClick={() => dismiss.mutate({ id: a.id, reason: dismissReason })}
                        disabled={!dismissReason || dismiss.isPending}
                      >
                        Confirm dismiss
                      </Button>
                      <Button className="min-h-9 px-3 text-xs" variant="secondary" onClick={() => setDismissId(null)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
