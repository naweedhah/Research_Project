"use client";

import Link from "next/link";
import { useMemo } from "react";
import {
  ArrowRight,
  ClipboardList,
  Stethoscope,
} from "lucide-react";
import {
  dedupeAttentionCases,
  presentAttentionCases,
  type AttentionCase,
  type AttentionQuery,
  type AttentionReason,
  type ClinicBoardGroups,
  type ClinicBoardPicture,
} from "@/data/clinic-board";
import { ageLabel, cn, formatPercent, formatStatus } from "@/utils/utils";

const OPEN_QUERY: AttentionQuery = {
  tab: "all",
  search: "",
  predictedType: "all",
  sex: "all",
  ageBand: "all",
  sort: "priority",
};

export function ClinicBoardScreen({
  groups,
}: {
  childCount: number;
  groups: ClinicBoardGroups;
  picture: ClinicBoardPicture;
}) {
  const cases = useMemo(() => dedupeAttentionCases(groups), [groups]);
  const round = useMemo(
    () => presentAttentionCases(cases, { ...OPEN_QUERY, sort: "priority", tab: "all" }),
    [cases],
  );

  return (
    <div className="relative -m-2 min-h-[calc(100vh-6rem)] overflow-x-hidden p-1 sm:-m-4 sm:p-2">
      <div className="relative mx-auto flex max-w-[1500px] flex-col gap-5">
        <BriefingBar />

        <section aria-label="Children to see this session">
          {round.length === 0 ? (
            <CalmEmpty />
          ) : (
            <ol className="grid gap-3 lg:grid-cols-2">
              {round.map((row, index) => (
                <li key={row.id}>
                  <RoundCard row={row} place={index + 1} />
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}

function BriefingBar() {
  return (
    <header className="flex items-center gap-2">
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-[#EAF7F6] text-[#0f766e]">
        <Stethoscope className="h-4 w-4" aria-hidden />
      </span>
      <h1 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#3E75B8]">Clinic round</h1>
    </header>
  );
}

function RoundCard({ row, place }: { row: AttentionCase; place: number }) {
  const name = row.full_name?.trim() || row.pseudonymous_id;
  const days = daysSinceVisit(row.last_visit);
  const stale = days != null && days >= 28;
  return (
    <article className="flex h-full flex-col rounded-[24px] border border-[#d7e4f2] bg-white p-4 shadow-[0_12px_32px_-24px_rgba(10,39,72,0.5)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#3E75B8]">#{place} this session</p>
          <h3 className="mt-1 truncate text-lg font-semibold text-[#0A2748]">{name}</h3>
          <p className="truncate text-xs text-[#64748b]">
            {row.full_name?.trim() ? `${row.pseudonymous_id} · ` : ""}
            {ageLabel(row.age_months)} · {formatStatus(row.sex)}
          </p>
        </div>
        {stale ? (
          <span className="shrink-0 rounded-full bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-900 ring-1 ring-amber-200">
            Last seen {days}d ago
          </span>
        ) : days != null ? (
          <span className="shrink-0 text-[11px] tabular-nums text-[#64748b]">Last visit {days}d ago</span>
        ) : null}
      </div>
      <CompareStrip row={row} />
      {row.reasons.some((reason) => reason !== "pattern-change") ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {row.reasons
            .filter((reason) => reason !== "pattern-change")
            .map((reason) => (
              <span key={reason} className={cn("rounded-full px-2 py-1 text-[11px] font-medium", chipClass(reason, row))}>
                {chipLabel(reason, row.weightDeltaKg)}
              </span>
            ))}
        </div>
      ) : null}
      {nextStep(row) ? (
        <p className="mt-2 text-xs leading-5 text-[#475569]">{nextStep(row)}</p>
      ) : null}
      <RowActions id={row.id} />
    </article>
  );
}

function CompareStrip({ row, compact }: { row: AttentionCase; compact?: boolean }) {
  return (
    <div className={cn("grid min-w-0 shrink-0 grid-cols-[1fr_auto_1fr] items-stretch gap-2", compact ? "mt-0" : "mt-3")}>
      <span className="min-w-0 rounded-xl bg-[#f0fdfa] px-3 py-2 ring-1 ring-emerald-100">
        <span className="block text-[10px] font-semibold uppercase tracking-wide text-[#0f766e]">Today · WHO</span>
        <span className="mt-0.5 block truncate text-sm font-semibold text-[#0A2748]">{row.whoLabel}</span>
      </span>
      <span className="flex items-center text-[#94a3b8]">
        <ArrowRight className="h-4 w-4" aria-hidden />
        <span className="sr-only">compared with 12-month prediction</span>
      </span>
      <span className="min-w-0 rounded-xl bg-[#eef2ff] px-3 py-2 ring-1 ring-[#c7d2fe]">
        <span className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[#4338ca]">Next 12 months</span>
          <span className="rounded-full bg-white/80 px-1.5 py-0.5 text-[9px] font-semibold text-[#4338ca]">GA-RGCA</span>
        </span>
        <span className="mt-0.5 block truncate text-sm font-semibold text-[#0A2748]">{row.predictedLabel}</span>
        {row.predictedTypeProbability != null ? (
          <span className="block text-[11px] tabular-nums text-[#4338ca]">
            {formatPercent(row.predictedTypeProbability)}
            {row.predictedLabel === "Normal" ? " highest condition risk" : " predicted risk"}
          </span>
        ) : null}
      </span>
    </div>
  );
}

function RowActions({ id }: { id: string }) {
  return (
    <div className="mt-4 flex w-full shrink-0 flex-wrap gap-2 pt-1">
      <Link
        href={`/children/${id}`}
        className="inline-flex h-10 items-center gap-1.5 rounded-xl bg-[#0E3A67] px-3 text-xs font-semibold text-white hover:bg-[#0A2748] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]"
      >
        <Stethoscope className="h-3.5 w-3.5" aria-hidden />
        Open profile
      </Link>
      <Link
        href={`/children/${id}/visits/new`}
        className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-[#e7eef6] bg-white px-3 text-xs font-semibold text-[#0A2748] hover:bg-[#f8fafc] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]"
      >
        <ClipboardList className="h-3.5 w-3.5" aria-hidden />
        Record visit
      </Link>
    </div>
  );
}

function CalmEmpty() {
  return (
    <div className="rounded-[24px] bg-[#f0fdfa] px-4 py-8 text-center text-sm text-[#115e59]">
      <p className="font-semibold">No children currently meet the Clinic Board attention rules.</p>
      <p className="mt-1 text-[#0f766e]">Continue routine monitoring and scheduled follow-up.</p>
    </div>
  );
}

function daysSinceVisit(iso?: string): number | null {
  if (!iso) return null;
  const day = iso.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const then = Date.parse(`${day}T00:00:00.000Z`);
  const now = Date.parse(`${new Date().toISOString().slice(0, 10)}T00:00:00.000Z`);
  if (!Number.isFinite(then) || !Number.isFinite(now)) return null;
  return Math.round((now - then) / 86_400_000);
}

function nextStep(row: AttentionCase): string {
  if (row.reasons.includes("future-risk")) {
    return "Well on today's WHO assessment. Confirm the 12-month forecast and decide whether closer follow-up is needed.";
  }
  if (row.reasons.includes("weight-decline")) {
    return "Recheck weight on the clinic scale, then record a visit if the drop is real.";
  }
  if (row.reasons.includes("pattern-change")) {
    return "";
  }
  return "Open the profile, separate today's WHO from the 12-month prediction, then record the next visit.";
}

function chipLabel(reason: AttentionReason, delta?: number) {
  if (reason === "future-risk") return "Well now → future risk";
  if (reason === "pattern-change") return "WHO ≠ 12-month type";
  if (delta == null) return "Weight down";
  return `Weight ${delta.toFixed(1)} kg`;
}

function chipClass(reason: AttentionReason, row: AttentionCase) {
  if (reason === "weight-decline") return "bg-sky-50 text-sky-950 ring-1 ring-sky-200";
  const label = reason === "pattern-change" ? `${row.whoLabel} ${row.predictedLabel}` : row.predictedLabel;
  if (label.includes("SAM")) return "bg-red-50 text-red-800";
  if (label.includes("MAM")) return "bg-orange-50 text-orange-900";
  if (label.includes("Stunting")) return "bg-violet-50 text-violet-900";
  if (label.includes("Underweight")) return "bg-amber-50 text-amber-900";
  return "bg-slate-100 text-slate-800";
}
