"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { cn } from "@/utils/utils";

type ComponentRow = {
  status: string;
  configured: boolean;
  pending_events?: number;
  failed_events?: number;
  last_success_at?: string | null;
};

type IntegrationStatus = {
  c3: ComponentRow;
  c4: ComponentRow;
  c2?: ComponentRow;
  integration_mode: string;
};

function linkTone(row?: ComponentRow) {
  const status = (row?.status ?? "NOT_CONFIGURED").toUpperCase();
  if (status === "CONNECTED") return "live";
  if (status === "DEGRADED") return "degraded";
  if (status === "OFFLINE") return "offline";
  return "ready";
}

function statusLabel(row?: ComponentRow) {
  const status = (row?.status ?? "NOT_CONFIGURED").toUpperCase();
  if (status === "CONNECTED") return "Linked · transferring";
  if (status === "DEGRADED") return "Linked · retrying queue";
  if (status === "OFFLINE") return "Queue held · partner offline";
  return "Contract ready · awaiting partner URL";
}

function FlowLane({
  side,
  tone,
  active,
  label,
  subtitle,
  statusText,
  pending,
}: {
  side: "left" | "right";
  tone: "live" | "degraded" | "offline" | "ready";
  active: boolean;
  label: string;
  subtitle: string;
  statusText: string;
  pending: number;
}) {
  return (
    <div className={cn("viva-flow-lane", side === "left" ? "viva-flow-lane-left" : "viva-flow-lane-right")}>
      <svg className="viva-flow-svg" viewBox="0 0 220 36" aria-hidden>
        <path
          className={cn("viva-flow-track", `viva-flow-track-${tone}`)}
          d={side === "left" ? "M210 18 H10" : "M10 18 H210"}
        />
        <path
          className={cn("viva-flow-packet", `viva-flow-packet-${tone}`, active && "is-active")}
          d={side === "left" ? "M210 18 H10" : "M10 18 H210"}
        />
      </svg>
      <div className={cn("viva-partner-card", `viva-partner-card-${tone}`)}>
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64748b]">{label}</p>
        <p className="mt-1 text-sm font-semibold text-[#0f2744]">{subtitle}</p>
        <p className="mt-1 text-xs text-[#475569]">{statusText}</p>
        {pending > 0 ? (
          <p className="mt-2 text-[11px] font-medium tabular-nums text-[#0A2748]">
            {pending} event{pending === 1 ? "" : "s"} in outbox
          </p>
        ) : (
          <p className="mt-2 text-[11px] text-[#94a3b8]">Outbox clear</p>
        )}
      </div>
    </div>
  );
}

export function IntegrationFlowPanel({ className }: { className?: string }) {
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<{ permissions?: string[] }>("/auth/me"),
  });
  const canReadIntegrations = (me.data?.permissions ?? []).some((p) => p === "research:read" || p === "admin:system");
  const { data } = useQuery({
    queryKey: ["integrations-status"],
    queryFn: () => api<IntegrationStatus>("/integrations/status"),
    enabled: canReadIntegrations,
    staleTime: 8_000,
    refetchInterval: canReadIntegrations ? 12_000 : false,
    retry: 1,
  });
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReducedMotion(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const c3Tone = linkTone(data?.c3);
  const c4Tone = linkTone(data?.c4);
  const c3Pending = data?.c3?.pending_events ?? 0;
  const c4Pending = data?.c4?.pending_events ?? 0;
  const c3Active = !reducedMotion && (c3Tone === "live" || c3Pending > 0);
  const c4Active = !reducedMotion && (c4Tone === "live" || c4Pending > 0);

  return (
    <section
      className={cn("viva-integration-panel no-print", className)}
      aria-label="Component integration data flow"
      data-testid="viva-integration-flow"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5b7c9a]">Viva integration view</p>
          <h2 className="mt-1 text-lg font-semibold text-[#0A2748]">Seamless C1 ↔ C3 ↔ C4 linkage</h2>
          <p className="mt-1 max-w-2xl text-sm text-[#475569]">
            Chanodya’s Component 1 owns child prediction and longitudinal monitoring, then transfers approved
            de-identified events to Shamiq (C3) and Naveed (C4) through versioned contracts — without sharing databases.
          </p>
        </div>
        <p className="rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-[#0f2744] ring-1 ring-[#d7e3ef]">
          Mode · {(data?.integration_mode ?? "…").toString()}
        </p>
      </div>

      <div className="viva-flow-stage mt-5">
        <FlowLane
          side="left"
          tone={c3Tone}
          active={c3Active}
          label="Component 3"
          subtitle="Shamiq · Counterfactuals"
          statusText={statusLabel(data?.c3)}
          pending={c3Pending}
        />

        <div className="viva-hub-card">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#93c5fd]">Component 1</p>
          <p className="mt-1 text-base font-semibold text-white">Chanodya · CNIP</p>
          <p className="mt-1 text-xs leading-snug text-white/75">
            Prediction · longitudinal progress · clinician review · durable outbox
          </p>
          <div className="mt-3 grid grid-cols-2 gap-2 text-[10px] text-white/80">
            <div className="rounded-lg bg-white/10 px-2 py-1.5">
              → C3 reassessment request
            </div>
            <div className="rounded-lg bg-white/10 px-2 py-1.5">
              → C4 prediction observation
            </div>
          </div>
        </div>

        <FlowLane
          side="right"
          tone={c4Tone}
          active={c4Active}
          label="Component 4"
          subtitle="Naveed · Drift monitoring"
          statusText={statusLabel(data?.c4)}
          pending={c4Pending}
        />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl bg-white/70 px-3 py-2.5 ring-1 ring-[#e2eaf3]">
          <p className="text-[11px] font-semibold text-[#0f2744]">What leaves C1</p>
          <p className="mt-1 text-xs text-[#64748b]">Pseudonymous IDs, visit references, and approved clinical features.</p>
        </div>
        <div className="rounded-xl bg-white/70 px-3 py-2.5 ring-1 ring-[#e2eaf3]">
          <p className="text-[11px] font-semibold text-[#0f2744]">What stays in C1</p>
          <p className="mt-1 text-xs text-[#64748b]">Clinical workflow, alerts, follow-ups, and model activation authority.</p>
        </div>
        <div className="rounded-xl bg-white/70 px-3 py-2.5 ring-1 ring-[#e2eaf3]">
          <p className="text-[11px] font-semibold text-[#0f2744]">If partners are offline</p>
          <p className="mt-1 text-xs text-[#64748b]">C1 keeps working. Events remain queued and retry — clinics are never blocked.</p>
        </div>
      </div>
    </section>
  );
}
