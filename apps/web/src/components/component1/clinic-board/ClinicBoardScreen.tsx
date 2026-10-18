"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, Info, Scale, Search, Stethoscope, Sun, Users } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import {
  dedupeAttentionCases,
  filterAttentionCases,
  needsAttentionIds,
  presentAttentionCases,
  type AttentionCase,
  type AttentionQuery,
  type AttentionReason,
  type AttentionTab,
  type ClinicBoardGroups,
  type ClinicBoardPicture,
  type PictureSlice,
} from "@/data/clinic-board";
import { ageLabel, cn, formatClinicalDate, formatPercent, formatStatus } from "@/utils/utils";

const OPEN_QUERY: AttentionQuery = {
  tab: "all",
  search: "",
  predictedType: "all",
  sex: "all",
  ageBand: "all",
  sort: "priority",
};

const TABS: { id: AttentionTab; label: string; short: string }[] = [
  { id: "all", label: "All attention", short: "All" },
  { id: "future-risk", label: "Future risk", short: "Risk" },
  { id: "pattern-change", label: "Pattern change", short: "Change" },
  { id: "weight-decline", label: "Weight decline", short: "Weight" },
];

export function ClinicBoardScreen({
  childCount,
  groups,
  picture,
}: {
  childCount: number;
  groups: ClinicBoardGroups;
  picture: ClinicBoardPicture;
}) {
  const [query, setQuery] = useState<AttentionQuery>(OPEN_QUERY);
  const cases = useMemo(() => dedupeAttentionCases(groups), [groups]);
  const priority = useMemo(
    () => presentAttentionCases(cases, { ...OPEN_QUERY, sort: "priority", tab: "all" }).slice(0, 4),
    [cases],
  );
  const visible = useMemo(() => presentAttentionCases(cases, query), [cases, query]);
  const tabCount = useMemo(
    () =>
      filterAttentionCases(cases, {
        ...query,
        search: "",
        predictedType: "all",
        sex: "all",
        ageBand: "all",
      }).length,
    [cases, query],
  );
  const attentionCount = needsAttentionIds(groups).length;
  const today = formatClinicalDate(new Date(), { day: "numeric", month: "short", year: "numeric" });

  const showWorklist = (
    tab: AttentionTab = "all",
  ) => {
    setQuery({ ...OPEN_QUERY, tab });
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.getElementById("attention-worklist")?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };

  return (
    <div className="relative -m-6 min-h-[calc(100vh-4rem)] overflow-x-hidden bg-[#F5F8FC] p-4 sm:p-6">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(14,116,144,0.09),transparent_42%),radial-gradient(ellipse_at_top_right,rgba(67,56,202,0.07),transparent_38%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(15,39,68,0.045)_1px,transparent_1px),linear-gradient(90deg,rgba(15,39,68,0.045)_1px,transparent_1px)] [background-size:28px_28px]"
        aria-hidden
      />
      <div className="relative mx-auto flex max-w-[1440px] flex-col gap-4">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-[#0E3A67]/10 pb-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#0E3A67]">Paediatric nutrition intelligence</p>
            <h1 className="mt-1 text-[1.75rem] font-semibold tracking-tight text-[#0A2748] sm:text-[2rem]">Clinic Board</h1>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[#475569]">
              Current undernutrition findings and 12-month predictive risk across the clinic.
            </p>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-white/70 bg-white/75 px-3 py-2 shadow-sm backdrop-blur-xl">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[#0f766e]">
              <span className="h-2 w-2 rounded-full bg-[#0f766e]" aria-hidden />
              Clinic list loaded
            </span>
            <span className="h-4 w-px bg-[#e2e8f0]" aria-hidden />
            <span className="text-xs tabular-nums text-[#334155]">{today}</span>
            <span className="rounded-full bg-[#0A2748] px-2.5 py-1 text-xs font-semibold tabular-nums text-white">{childCount} children</span>
          </div>
        </header>

        <ClinicPulse
          childCount={childCount}
          attentionCount={attentionCount}
          futureRisk={groups.wellTodayPredictedRisk.length}
          mismatch={groups.undernourishedTodayDifferentPrediction.length}
          weight={groups.weightLowerThanLastVisit.length}
          onOpen={showWorklist}
        />

        <section aria-labelledby="priority-heading" className="rounded-[24px] border border-[#e7eef6] bg-white p-4 shadow-[0_8px_30px_rgba(15,40,80,0.05)]">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 id="priority-heading" className="text-base font-semibold text-[#0A2748]">Priority attention</h2>
              <p className="mt-0.5 text-xs text-[#64748b]">Worklist order only. This is not a validated clinical severity score.</p>
            </div>
            <button type="button" onClick={() => showWorklist("all")} className="text-xs font-semibold text-[#0E3A67] hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]">
              View all
            </button>
          </div>
          {priority.length === 0 ? (
            <CalmEmpty />
          ) : (
            <ul className="mt-3 divide-y divide-[#eef2f6]">
              {priority.map((row) => (
                <AttentionRow key={row.id} row={row} />
              ))}
            </ul>
          )}
        </section>

        <div className="order-2 flex flex-col gap-4 lg:order-none">
          <ClinicIntelligence picture={picture} />
        </div>

        <section id="attention-worklist" className="order-1 scroll-mt-24 rounded-[24px] border border-white/70 bg-white/80 p-4 shadow-[0_8px_30px_rgba(15,40,80,0.05)] backdrop-blur-xl lg:order-none">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <h2 className="text-base font-semibold text-[#0A2748]">Attention worklist</h2>
            <p className="text-xs tabular-nums text-[#64748b]">
              Showing {visible.length} of {tabCount}
            </p>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4" role="tablist" aria-label="Attention groups">
            {TABS.map((tab) => {
              const count = tab.id === "all" ? attentionCount : groupsFor(groups, tab.id).length;
              const selected = query.tab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  id={`attention-tab-${tab.id}`}
                  aria-selected={selected}
                  aria-pressed={selected}
                  aria-controls="attention-worklist-panel"
                  onClick={() => setQuery((current) => ({ ...current, tab: tab.id }))}
                  className={cn(
                    "rounded-2xl border px-3 py-2 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]",
                    selected ? "border-[#0E3A67] bg-[#EAF2FA]" : "border-[#e7eef6] bg-white hover:border-[#cbd5e1]",
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-sm font-semibold text-[#0A2748]">
                      <span className={cn("h-1.5 w-1.5 rounded-full", selected ? "bg-[#0E3A67]" : "bg-[#cbd5e1]")} aria-hidden />
                      <span className="sm:hidden">{tab.short}</span>
                      <span className="hidden sm:inline">{tab.label}</span>
                    </span>
                    <span className="text-lg font-semibold tabular-nums text-[#0A2748]">{count}</span>
                  </span>
                  <span className="mt-0.5 block text-[11px] leading-snug text-[#64748b]">{tabHint(tab.id)}</span>
                  <span className="mt-1 block text-[11px] tabular-nums text-[#64748b]">{share(count, childCount)} of clinic</span>
                </button>
              );
            })}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="relative min-w-[200px] flex-1">
              <span className="sr-only">Search child or ID</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#94a3b8]" aria-hidden />
              <input
                value={query.search}
                onChange={(event) => setQuery((current) => ({ ...current, search: event.target.value }))}
                placeholder="Search child or ID"
                className="h-10 w-full rounded-xl border border-[#e7eef6] bg-white pl-8 pr-3 text-sm text-[#0A2748] placeholder:text-[#94a3b8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]"
              />
            </label>
            <FilterSelect label="Predicted type" value={query.predictedType} onChange={(predictedType) => setQuery((current) => ({ ...current, predictedType: predictedType as AttentionQuery["predictedType"] }))} options={["all", "Underweight", "Stunting", "MAM", "SAM"]} />
            <FilterSelect label="Age" value={query.ageBand} onChange={(ageBand) => setQuery((current) => ({ ...current, ageBand: ageBand as AttentionQuery["ageBand"] }))} options={["all", "0-5", "6-11", "12-23", "24-35", "36-47", "48-60"]} optionLabel={ageOption} />
            <FilterSelect label="Sex" value={query.sex} onChange={(sex) => setQuery((current) => ({ ...current, sex: sex as AttentionQuery["sex"] }))} options={["all", "female", "male"]} optionLabel={(value) => (value === "all" ? "All" : formatStatus(value))} />
            <FilterSelect label="Sort" value={query.sort} onChange={(sort) => setQuery((current) => ({ ...current, sort: sort as AttentionQuery["sort"] }))} options={["priority", "visit", "age", "name"]} optionLabel={sortOption} />
          </div>

          <div id="attention-worklist-panel" role="tabpanel" aria-labelledby={`attention-tab-${query.tab}`} className="mt-3">
          {visible.length === 0 ? (
            cases.length === 0 ? (
              <CalmEmpty />
            ) : (
              <p className="rounded-2xl bg-[#f8fafc] px-4 py-8 text-center text-sm text-[#64748b]">No children currently meet this monitoring rule.</p>
            )
          ) : query.tab === "weight-decline" ? (
            <ul className="mt-3 space-y-2">
              {visible.map((row) => (
                <WeightChangeRow key={row.id} row={row} />
              ))}
            </ul>
          ) : (
            <ul className="mt-3 divide-y divide-[#eef2f6]">
              {visible.map((row) => (
                <AttentionRow key={row.id} row={row} />
              ))}
            </ul>
          )}
          </div>
        </section>
      </div>
    </div>
  );
}

function ClinicPulse({
  childCount,
  attentionCount,
  futureRisk,
  mismatch,
  weight,
  onOpen,
}: {
  childCount: number;
  attentionCount: number;
  futureRisk: number;
  mismatch: number;
  weight: number;
  onOpen: (tab: AttentionTab) => void;
}) {
  return (
    <section aria-label="Clinic pulse" className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      <PulseCard icon={Users} label="Children" value={childCount} detail="On the clinic list" tone="navy" />
      <PulseCard icon={Stethoscope} label="Needs attention" value={attentionCount} detail="Unique children in any tray" tone="amber" dominant onClick={() => onOpen("all")} />
      <PulseCard icon={Sun} label="Future risk while well" value={futureRisk} detail={share(futureRisk, childCount)} tone="amber" onClick={() => onOpen("future-risk")} />
      <PulseCard icon={Info} label="Current–future mismatch" value={mismatch} detail={share(mismatch, childCount)} tone="navy" onClick={() => onOpen("pattern-change")} />
      <PulseCard icon={Scale} label="Weight decline" value={weight} detail={share(weight, childCount)} tone="cyan" onClick={() => onOpen("weight-decline")} />
    </section>
  );
}

function PulseCard({
  icon: Icon,
  label,
  value,
  detail,
  tone,
  dominant,
  onClick,
}: {
  icon: typeof Users;
  label: string;
  value: number;
  detail: string;
  tone: "navy" | "amber" | "red" | "cyan";
  dominant?: boolean;
  onClick?: () => void;
}) {
  const ink = tone === "amber" ? "#b45309" : tone === "red" ? "#b91c1c" : tone === "cyan" ? "#0369a1" : "#0A2748";
  const body = (
    <>
      <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#f8fafc]" style={{ color: ink }}>
        <Icon className="h-4 w-4" aria-hidden />
      </span>
      <p className={cn("mt-2 font-semibold tabular-nums tracking-tight text-[#0A2748]", dominant ? "text-4xl" : "text-3xl")}>{value}</p>
      <p className="mt-1 text-sm font-semibold text-[#0A2748]">{label}</p>
      <p className="text-[11px] text-[#64748b]">{detail}</p>
    </>
  );
  const className = cn(
    "rounded-[24px] border bg-white/80 p-3 text-left shadow-sm backdrop-blur-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]",
    dominant ? "border-[#d97706]/50 ring-1 ring-[#d97706]/20" : "border-white/80",
    onClick ? "motion-safe:transition-transform motion-safe:hover:-translate-y-px" : "",
  );
  if (!onClick) return <article className={className}>{body}</article>;
  return (
    <button type="button" onClick={onClick} className={className}>
      {body}
    </button>
  );
}

function ClinicIntelligence({ picture }: { picture: ClinicBoardPicture }) {
  return (
    <section aria-labelledby="intelligence-heading" className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 id="intelligence-heading" className="text-base font-semibold text-[#0A2748]">Clinic intelligence</h2>
      </div>
      <p className="flex items-start gap-2 rounded-2xl border border-[#dbe7f3] bg-white/70 px-3 py-2 text-xs leading-relaxed text-[#334155]">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#0E3A67]" aria-hidden />
        Current WHO undernutrition findings describe the latest measured anthropometry. GA-RGCA estimates future nutritional risk over the next 12 months. They represent different time points.
      </p>
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto_minmax(280px,0.9fr)_auto_minmax(0,1fr)] xl:items-stretch">
        <DistributionCard
          eyebrow="Latest assessment"
          title="Current undernutrition profile"
          definition="Current anthropometric undernutrition assessment."
          slices={picture.measured}
          total={picture.children}
        />
        <TimeArrow />
        <AlignmentCard slices={picture.alignment} total={picture.children} />
        <TimeArrow />
        <DistributionCard
          eyebrow="GA-RGCA"
          title="12-month predicted risk profile"
          definition="Multimodal model estimating 12-month nutritional risk."
          slices={picture.predicted}
          total={picture.children}
          predictive
        />
      </div>
    </section>
  );
}

function TimeArrow() {
  return (
    <div className="hidden items-center justify-center text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64748b] xl:flex" aria-hidden>
      <span className="flex flex-col items-center gap-1">
        <ArrowRight className="h-4 w-4" />
        Horizon
      </span>
    </div>
  );
}

function AlignmentCard({ slices, total }: { slices: PictureSlice[]; total: number }) {
  const data = slices.filter((slice) => slice.count > 0);
  const same = slices.find((slice) => slice.key === "same")?.count ?? 0;
  const sameShare = total > 0 ? Math.round((same / total) * 100) : 0;
  const summary = slices.map((slice) => `${slice.label} ${slice.count}`).join(", ");
  return (
    <article className="rounded-[24px] bg-[#0A2748] p-4 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/80">Current–future alignment</p>
      <h3 className="mt-1 text-base font-semibold">Latest finding and 12-month type</h3>
      <p className="sr-only">{summary}</p>
      <div className="relative mt-2 h-36" aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data.length ? data : [{ key: "empty", label: "None", count: 1, color: "#1e3a5f" }]} dataKey="count" nameKey="label" innerRadius={46} outerRadius={64} paddingAngle={2} stroke="none">
              {(data.length ? data : [{ key: "empty", color: "#1e3a5f" }]).map((slice) => (
                <Cell key={slice.key} fill={slice.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <p className="text-2xl font-semibold tabular-nums">{sameShare}%</p>
          <p className="text-[11px] text-white/85">Same pattern</p>
        </div>
      </div>
      <ul className="space-y-1">
        {slices.map((slice) => (
          <li key={slice.key} className="flex items-center gap-2 text-xs">
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: slice.color }} />
            <span className="min-w-0 flex-1 text-white/90">{slice.label}</span>
            <span className="tabular-nums font-semibold">{slice.count}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[11px] leading-relaxed text-white/80">
        A different pattern is not a model error. The two assessments cover different time points.
      </p>
    </article>
  );
}

function DistributionCard({
  eyebrow,
  title,
  definition,
  slices,
  total,
  predictive,
}: {
  eyebrow: string;
  title: string;
  definition: string;
  slices: PictureSlice[];
  total: number;
  predictive?: boolean;
}) {
  const max = Math.max(1, ...slices.map((slice) => slice.count));
  return (
    <article className={cn("rounded-[24px] border bg-white p-4 shadow-sm", predictive ? "border-[#c7d2fe]" : "border-[#e7eef6]")}>
      <div className={cn("mb-2 h-0.5 w-10 rounded-full", predictive ? "bg-[#4338ca]" : "bg-[#0f766e]")} aria-hidden />
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#0E3A67]">{eyebrow}</p>
      <h3 className="mt-1 text-base font-semibold text-[#0A2748]">{title}</h3>
      <p className="mt-0.5 text-[11px] text-[#64748b]">{definition}</p>
      <ul className="mt-3 space-y-2">
        {slices.map((slice) => (
          <li key={slice.key}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
              <span className="text-[#334155]">{slice.label}</span>
              <span className="shrink-0 tabular-nums text-[#64748b]">
                <span className="font-semibold text-[#0A2748]">{slice.count}</span>
                {" · "}
                {share(slice.count, total)}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-[#eef2f6]">
              <div
                className="h-full rounded-full motion-safe:transition-[width]"
                style={{ width: `${(slice.count / max) * 100}%`, background: slice.color, minWidth: slice.count > 0 ? 6 : 0 }}
              />
            </div>
          </li>
        ))}
      </ul>
    </article>
  );
}

function AttentionRow({ row }: { row: AttentionCase }) {
  const name = row.full_name?.trim() || row.pseudonymous_id;
  return (
    <li className="grid gap-3 py-3 lg:grid-cols-[minmax(160px,0.9fr)_minmax(280px,1.5fr)_minmax(160px,0.9fr)_auto] lg:items-center">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-[#0A2748]">{name}</p>
        <p className="truncate text-xs text-[#64748b]">
          {row.full_name?.trim() ? `${row.pseudonymous_id} · ` : ""}
          {ageLabel(row.age_months)} · {formatStatus(row.sex)}
          {row.last_visit ? ` · ${formatClinicalDate(row.last_visit)}` : ""}
        </p>
      </div>
      <Horizon row={row} />
      <ReasonChips row={row} />
      <RowActions id={row.id} />
    </li>
  );
}

function Horizon({ row }: { row: AttentionCase }) {
  return (
    <div className="flex items-stretch gap-2">
      <span className="min-w-0 flex-1 rounded-xl bg-[#f8fafc] px-3 py-2 ring-1 ring-[#e7eef6]">
        <span className="block text-[10px] font-semibold uppercase tracking-wide text-[#64748b]">Today · WHO</span>
        <span className="mt-0.5 block truncate text-sm font-semibold text-[#0A2748]">{row.whoLabel}</span>
      </span>
      <span className="flex items-center text-[#64748b]">
        <span className="sr-only">compared with</span>
        <ArrowRight className="h-4 w-4" aria-hidden />
      </span>
      <span className="min-w-0 flex-1 rounded-xl bg-[#eef2ff] px-3 py-2 ring-1 ring-[#c7d2fe]">
        <span className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[#4338ca]">Next 12 months</span>
          <span className="rounded-full bg-white/80 px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-[#4338ca]">GA-RGCA</span>
        </span>
        <span className="mt-0.5 block truncate text-sm font-semibold text-[#0A2748]">{row.predictedLabel}</span>
        {row.predictedTypeProbability != null ? (
          <span className="block text-[11px] tabular-nums text-[#4338ca]">
            {formatPercent(row.predictedTypeProbability)}
            {row.predictedLabel === "Normal" ? "" : " predicted risk"}
          </span>
        ) : null}
      </span>
    </div>
  );
}

function ReasonChips({ row }: { row: AttentionCase }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {row.reasons.map((reason) => (
        <span key={reason} className={cn("rounded-full px-2 py-1 text-[11px] font-medium", chipClass(reason, row))}>
          {chipLabel(reason, row.weightDeltaKg)}
        </span>
      ))}
    </div>
  );
}

function WeightChangeRow({ row }: { row: AttentionCase }) {
  const name = row.full_name?.trim() || row.pseudonymous_id;
  const delta = row.weightDeltaKg;
  return (
    <li className="grid gap-3 rounded-2xl border border-[#e7eef6] bg-white p-3 lg:grid-cols-[minmax(140px,0.8fr)_minmax(240px,1.4fr)_auto] lg:items-center">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-[#0A2748]">{name}</p>
        <p className="text-xs text-[#64748b]">{row.pseudonymous_id}</p>
      </div>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[#64748b]">Recorded weight change</p>
        <p className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm text-[#0A2748]">
          <span>Previous {row.previousWeightKg != null ? `${row.previousWeightKg.toFixed(1)} kg` : "—"}</span>
          <span className="text-[#64748b]" aria-hidden>→</span>
          <span>Latest {row.weightKg != null ? `${row.weightKg.toFixed(1)} kg` : "—"}</span>
          {delta != null ? <span className="font-semibold tabular-nums text-[#0369a1]">Change {delta.toFixed(1)} kg</span> : null}
        </p>
        <div className="mt-2">
          <ReasonChips row={row} />
        </div>
      </div>
      <RowActions id={row.id} />
    </li>
  );
}

function RowActions({ id }: { id: string }) {
  return (
    <div className="flex shrink-0 gap-2">
      <Link href={`/children/${id}`} className="inline-flex h-9 items-center rounded-xl bg-[#0E3A67] px-3 text-xs font-semibold text-white hover:bg-[#0A2748] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]">
        Review child
      </Link>
      <Link href={`/children/${id}/visits/new`} className="inline-flex h-9 items-center rounded-xl border border-[#e7eef6] bg-white px-3 text-xs font-semibold text-[#0A2748] hover:bg-[#f8fafc] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]">
        Record visit
      </Link>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
  optionLabel,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  optionLabel?: (value: string) => string;
}) {
  return (
    <label className="text-[11px] font-medium text-[#64748b]">
      <span className="sr-only">{label}</span>
      <select
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-xl border border-[#e7eef6] bg-white px-2 text-xs text-[#0A2748] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E3A67]"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {label}: {optionLabel ? optionLabel(option) : option === "all" ? "All" : option}
          </option>
        ))}
      </select>
    </label>
  );
}

function CalmEmpty() {
  return (
    <div className="mt-3 rounded-2xl bg-[#f0fdfa] px-4 py-6 text-sm text-[#115e59]">
      <p className="font-semibold">No children currently meet the Clinic Board attention rules.</p>
      <p className="mt-1 text-[#0f766e]">Continue routine monitoring and scheduled follow-up.</p>
    </div>
  );
}

function groupsFor(groups: ClinicBoardGroups, tab: AttentionReason) {
  if (tab === "future-risk") return groups.wellTodayPredictedRisk;
  if (tab === "pattern-change") return groups.undernourishedTodayDifferentPrediction;
  return groups.weightLowerThanLastVisit;
}

function share(count: number, total: number) {
  if (total <= 0) return "0%";
  return `${Math.round((count / total) * 100)}%`;
}

function tabHint(tab: AttentionTab) {
  if (tab === "future-risk") return "No current WHO undernutrition finding, but the 12-month model predicts an undernutrition type.";
  if (tab === "pattern-change") return "The latest WHO finding and the predicted 12-month type are different patterns.";
  if (tab === "weight-decline") return "Weight is at least 0.1 kg below the previous recorded visit.";
  return "Each child is listed once, with every attention reason that applies.";
}

function chipLabel(reason: AttentionReason, delta?: number) {
  if (reason === "future-risk") return "Early-risk signal";
  if (reason === "pattern-change") return "Pattern change";
  if (delta == null) return "Weight decline";
  return `Weight ↓ ${Math.abs(delta).toFixed(1)} kg`;
}

function chipClass(reason: AttentionReason, row: AttentionCase) {
  if (reason === "weight-decline") {
    const acute = row.predictedLabel === "SAM" || row.predictedLabel === "MAM" || row.whoLabel.includes("SAM") || row.whoLabel.includes("MAM");
    return acute ? "bg-sky-50 text-sky-950 ring-1 ring-sky-200" : "bg-sky-50 text-sky-900";
  }
  const label = reason === "pattern-change" ? `${row.whoLabel} ${row.predictedLabel}` : row.predictedLabel;
  if (label.includes("SAM")) return "bg-red-50 text-red-800";
  if (label.includes("MAM")) return "bg-orange-50 text-orange-900";
  if (label.includes("Stunting")) return "bg-violet-50 text-violet-900";
  if (label.includes("Underweight")) return "bg-amber-50 text-amber-900";
  return "bg-slate-100 text-slate-800";
}

function ageOption(value: string) {
  if (value === "all") return "All";
  return `${value} mo`;
}

function sortOption(value: string) {
  if (value === "priority") return "Priority";
  if (value === "visit") return "Latest visit";
  if (value === "age") return "Age";
  return "Name / ID";
}
