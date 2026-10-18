"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Select } from "@/components/common/field";
import { StatusBadge } from "@/components/cards/status-badge";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";
import { formatPercent, formatStatus } from "@/utils/utils";
import { useState } from "react";
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

const STATUS_TABS = ["OPEN", "IN_REVIEW", "ACKNOWLEDGED", "RESOLVED", "DISMISSED_WITH_REASON"] as const;

export default function AlertsPage() {
  const qc = useQueryClient();
  const [type, setType] = useState("");
  const [status, setStatus] = useState<string>("OPEN");
  const [dismissId, setDismissId] = useState<string | null>(null);
  const [dismissReason, setDismissReason] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["alerts", type, status],
    queryFn: () => api<{ items: Alert[] }>(`/alerts?type=${type}&status=${status}`),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["alerts"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const ack = useMutation({
    mutationFn: (id: string) => api(`/alerts/${id}/acknowledge`, { method: "PATCH", body: JSON.stringify({}) }),
    onSuccess: () => {
      toast.success("Alert acknowledged");
      invalidate();
    },
  });
  const review = useMutation({
    mutationFn: (id: string) => api(`/alerts/${id}/review`, { method: "PATCH", body: JSON.stringify({}) }),
    onSuccess: () => {
      toast.success("Alert marked in review");
      invalidate();
    },
  });
  const resolve = useMutation({
    mutationFn: (id: string) => api(`/alerts/${id}/resolve`, { method: "PATCH", body: JSON.stringify({ notes: "Reviewed in clinic" }) }),
    onSuccess: () => {
      toast.success("Alert resolved");
      invalidate();
    },
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
  });

  if (isLoading) return <Skeleton className="h-64" />;
  if (error) return <ErrorState message="Unable to load alerts." />;
  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#0f2744]">Alert centre</h1>
        </div>
        <div className="flex flex-wrap justify-end gap-3">
        <Select
          className="w-auto min-w-[12.5rem] rounded-lg"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          aria-label="Alert status"
        >
          {STATUS_TABS.map((s) => (
            <option key={s} value={s}>
              {formatStatus(s)}
            </option>
          ))}
        </Select>
        <Select
          className="w-auto min-w-[12.5rem] rounded-lg"
          value={type}
          onChange={(e) => setType(e.target.value)}
          aria-label="Alert type"
        >
          <option value="">All alert types</option>
          <option value="STAGNATION">{formatStatus("STAGNATION")}</option>
          <option value="DETERIORATION">{formatStatus("DETERIORATION")}</option>
          <option value="RELAPSE">{formatStatus("RELAPSE")}</option>
          <option value="MISSED_FOLLOW_UP">{formatStatus("MISSED_FOLLOW_UP")}</option>
        </Select>
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState title="No alerts in this view." body="Change status or type filters to see other alerts." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((a) => (
            <article key={a.id} className="rounded-2xl border border-line bg-white p-5 shadow-card">
              <div className="flex justify-between gap-2">
                <div>
                  <p className="font-semibold">{a.pseudonymous_id}</p>
                  <p className="text-xs text-muted">{formatStatus(a.type)} · {new Date(a.created_at).toLocaleString()}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <StatusBadge value={a.severity} />
                  <StatusBadge value={a.status} />
                </div>
              </div>
              <p className="mt-3 text-sm leading-relaxed">{a.message}</p>
              {a.trigger_value?.previous_risk != null && a.trigger_value?.current_risk != null ? (
                <p className="mt-2 text-sm text-muted">
                  {a.trigger_value?.basis === "predicted_risk_change" ? "Highest predicted condition risk" : "Model score"}:{" "}
                  {formatPercent(a.trigger_value.previous_risk)} → {formatPercent(a.trigger_value.current_risk)}
                </p>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href={`/children/${a.child_id}`}>
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
          ))}
        </div>
      )}
    </div>
  );
}
