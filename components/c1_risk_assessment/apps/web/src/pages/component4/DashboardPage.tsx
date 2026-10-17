"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CalendarClock,
  CalendarX2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  HelpCircle,
  Info,
  Minus,
  PauseCircle,
  Stethoscope,
  TrendingDown,
  Users,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api } from "@/services/component4/httpClient";
import { StatusBadge } from "@/components/cards/status-badge";
import { Button } from "@/components/common/button";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";
import { displayedMalnutritionType } from "@/data/child-profile";
import { ageLabel, formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { useMemo, useState, useRef, useEffect, type ReactNode } from "react";

type PriorityAlert = {
  type: string;
  severity: string;
  status: string;
  id: string | null;
};

type PriorityPatient = {
  child_id: string;
  pseudonymous_id: string;
  full_name?: string | null;
  age_months?: number;
  sex?: string;
  latest_visit?: string | null;
  current_status?: string | null;
  predicted_malnutrition_type?: string | null;
  detected_conditions?: string[] | null;
  score_kind?: string;
  severity?: string | null;
  probability_label: string;
  current_probability?: number | null;
  previous_probability?: number | null;
  probability_delta_pp?: number | null;
  risk_velocity?: number | null;
  progress_state?: string | null;
  alerts: PriorityAlert[];
  review_status: string;
};

type Dashboard = {
  synthetic: boolean;
  facility: { name: string | null; code: string | null };
  model: { label: string; version: string; is_demo: boolean };
  generated_at: string;
  kpis: {
    children_under_monitoring: number;
    awaiting_clinical_review: number;
    deteriorating: number;
    stagnating: number;
    overdue_follow_ups: number;
    open_alerts: number;
  };
  priority_patients: PriorityPatient[];
  risk_trend: {
    improving: number;
    stable: number;
    stagnating: number;
    deteriorating: number;
    insufficient_history: number;
    total_classified: number;
  };
  longitudinal_intelligence: {
    children_with_two_plus_assessments: number;
    active_progress_alerts: number;
    comparable_trajectories: number;
  };
  follow_ups: {
    overdue: FollowUpItem[];
    today: FollowUpItem[];
    upcoming: FollowUpItem[];
    total_scheduled: number;
  };
  recent_clinical_reviews: {
    note_id: string;
    child_id: string;
    pseudonymous_id?: string | null;
    full_name?: string | null;
    assessment: string;
    assessment_key?: string;
    workflow?: string | null;
    workflow_key?: string | null;
    reviewer_name?: string | null;
    note_excerpt?: string | null;
    created_at: string;
  }[];
};

type FollowUpItem = {
  child: string | null;
  full_name?: string | null;
  child_id: string;
  date: string;
  clinic: string | null;
  status: string;
  overdue_days?: number | null;
};

type QueueFilter = "all" | "awaiting" | "deteriorating" | "stagnating" | "followup_overdue";

const PROGRESS_COLORS: Record<string, string> = {
  Improving: "#059669",
  Stable: "#64748b",
  Stagnating: "#d97706",
  Deteriorating: "#dc2626",
  "Insufficient history": "#94a3b8",
};

const REVIEW_LABELS: Record<string, string> = {
  AWAITING_REVIEW: "Awaiting Review",
  REVIEWED: "Reviewed",
  IN_REVIEW: "In Review",
  FURTHER_ASSESSMENT: "Further Assessment",
  DISAGREED: "Disagree",
  NOT_REQUIRED: "Not required",
};

function hasAlertType(row: PriorityPatient, type: string) {
  return row.alerts.some((a) => a.type === type);
}

function queueMatchesFilter(row: PriorityPatient, filter: QueueFilter) {
  if (filter === "all") return true;
  if (filter === "awaiting") return row.review_status === "AWAITING_REVIEW";
  if (filter === "deteriorating") return row.progress_state === "deteriorating" || hasAlertType(row, "DETERIORATION");
  if (filter === "stagnating") return row.progress_state === "stagnating" || hasAlertType(row, "STAGNATION");
  if (filter === "followup_overdue") return hasAlertType(row, "MISSED_FOLLOW_UP");
  return true;
}

function formatDeltaPp(delta?: number | null) {
  if (delta === null || delta === undefined) return null;
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta} pp`;
}

function formatRiskVelocity(rv?: number | null) {
  if (rv === null || rv === undefined) return "Not available";
  const ppMonth = (rv * 100).toFixed(1);
  return `${Number(ppMonth) > 0 ? "+" : ""}${ppMonth} pp/month`;
}

export default function DashboardPage() {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api<Dashboard>("/dashboard"),
  });
  const [filter, setFilter] = useState<QueueFilter>("all");

  const filtered = useMemo(
    () => (data ? data.priority_patients.filter((row) => queueMatchesFilter(row, filter)) : []),
    [data, filter],
  );

  const progressChart = useMemo(() => {
    if (!data) return [];
    const items = [
      { name: "Improving", n: data.risk_trend.improving },
      { name: "Stable", n: data.risk_trend.stable },
      { name: "Stagnating", n: data.risk_trend.stagnating },
      { name: "Deteriorating", n: data.risk_trend.deteriorating },
    ];
    if (data.risk_trend.insufficient_history > 0) {
      items.push({ name: "Insufficient history", n: data.risk_trend.insufficient_history });
    }
    const total = items.reduce((s, i) => s + i.n, 0);
    return items.map((item) => ({
      ...item,
      fill: PROGRESS_COLORS[item.name] ?? "#64748b",
      pct: total > 0 ? Math.round((item.n / total) * 100) : 0,
    }));
  }, [data]);

  const progressTotal = useMemo(() => progressChart.reduce((s, i) => s + i.n, 0), [progressChart]);
  const progressPieData = useMemo(() => progressChart.filter((item) => item.n > 0), [progressChart]);

  if (isLoading) {
    return (
      <div className="min-w-[1240px] space-y-4">
        <Skeleton className="h-28" />
        <div className="grid grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <ErrorState message="Clinical dashboard data could not be loaded." />
        <div className="text-center">
          <Button type="button" onClick={() => refetch()} disabled={isFetching}>
            Retry
          </Button>
        </div>
      </div>
    );
  }


  const focusQueue = (next: QueueFilter) => {
    setFilter(next);
    document.getElementById("review-queue")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="min-w-[1240px] space-y-5">
      <header>
        <h1 className="text-2xl font-bold text-[#0f2744]">Dashboard</h1>
      </header>

      <section className="grid grid-cols-5 gap-3">
        <SummaryTile
          label="Children Under Monitoring"
          value={data.kpis.children_under_monitoring}
          href="/children"
          icon={Users}
          selected={false}
        />
        <SummaryTile
          label="Awaiting Clinical Review"
          value={data.kpis.awaiting_clinical_review}
          accent={data.kpis.awaiting_clinical_review > 0 ? "amber" : undefined}
          icon={ClipboardList}
          selected={filter === "awaiting"}
          onClick={() => focusQueue("awaiting")}
        />
        <SummaryTile
          label="Deteriorating"
          value={data.kpis.deteriorating}
          accent={data.kpis.deteriorating > 0 ? "red" : undefined}
          icon={TrendingDown}
          selected={filter === "deteriorating"}
          onClick={() => focusQueue("deteriorating")}
        />
        <SummaryTile
          label="Stagnating"
          value={data.kpis.stagnating}
          accent={data.kpis.stagnating > 0 ? "amber" : undefined}
          icon={PauseCircle}
          selected={filter === "stagnating"}
          onClick={() => focusQueue("stagnating")}
        />
        <SummaryTile
          label="Overdue Follow-Ups"
          value={data.kpis.overdue_follow_ups}
          accent={data.kpis.overdue_follow_ups > 0 ? "amber" : undefined}
          icon={CalendarX2}
          selected={filter === "followup_overdue"}
          onClick={() => focusQueue("followup_overdue")}
        />
      </section>

      <section id="review-queue" className="rounded-3xl bg-white p-5 shadow-[0_4px_24px_rgba(15,40,80,0.06)]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 shrink">
            <h2 className="text-base font-semibold text-[#0f2744]">Patients Requiring Review</h2>
          </div>
          <div className="flex shrink-0 flex-nowrap gap-1.5 overflow-x-auto" role="tablist" aria-label="Priority patient filters">
            {(
              [
                ["all", "All"],
                ["awaiting", "Awaiting Review"],
                ["deteriorating", "Deteriorating"],
                ["stagnating", "Stagnating"],
                ["followup_overdue", "Follow-Up Overdue"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={filter === key}
                onClick={() => setFilter(key)}
                className={`shrink-0 rounded-lg px-3 py-1 text-xs font-medium transition ${
                  filter === key ? "bg-[#2563eb] text-white" : "bg-[#f1f5f9] text-[#475569] hover:bg-[#e2e8f0]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 max-h-[min(36rem,58vh)] space-y-3 overflow-y-auto pr-1">
          {filtered.length === 0 ? (
            <EmptyState
              title="No patients currently require priority review."
              body="New deterioration, stagnation or assessment-review events will appear here."
            />
          ) : (
            filtered.map((row) => <PriorityPatientRow key={row.child_id} row={row} />)
          )}
        </div>
      </section>

      <div className="grid grid-cols-2 gap-5">
        <ProgressOverviewSection items={progressChart} pieData={progressPieData} total={progressTotal} />

        <FollowUpWorklistSection followUps={data.follow_ups} />
      </div>

      {data.recent_clinical_reviews.length > 0 ? (
        <RecentClinicalReviewsSection reviews={data.recent_clinical_reviews} />
      ) : null}
    </div>
  );
}

function formatReviewWhen(iso: string) {
  const date = new Date(iso);
  const time = date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  const isToday = date.toDateString() === new Date().toDateString();
  if (isToday) return `Today · ${time}`;
  return `${date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })} · ${time}`;
}

const REVIEW_ASSESSMENT_STYLES: Record<string, { icon: LucideIcon; tone: string }> = {
  agree: { icon: CheckCircle2, tone: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  disagree: { icon: XCircle, tone: "bg-red-50 text-red-800 border-red-200" },
  uncertain: { icon: HelpCircle, tone: "bg-amber-50 text-amber-800 border-amber-200" },
  reviewed: { icon: ClipboardList, tone: "bg-slate-50 text-slate-700 border-slate-200" },
};

function RecentClinicalReviewsSection({
  reviews,
}: {
  reviews: Dashboard["recent_clinical_reviews"];
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollByCard = (direction: 1 | -1) => {
    const container = scrollRef.current;
    if (!container || container.children.length === 0) return;
    const card = container.children[0] as HTMLElement;
    const step = card.offsetWidth + 12;
    container.scrollBy({ left: direction * step, behavior: "smooth" });
  };

  return (
    <section className="overflow-hidden rounded-3xl border border-[#e8eef5] bg-gradient-to-r from-[#f0f6fc] via-white to-[#f0f6fc] p-5 shadow-[0_4px_24px_rgba(15,40,80,0.06)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-[#0f2744]">Recent Clinical Reviews</h2>
          <p className="mt-1 text-xs text-[#64748b]">Use the arrows to browse latest clinician responses</p>
        </div>
        <span className="shrink-0 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-[#475569] shadow-sm">
          {reviews.length} recent
        </span>
      </div>

      <div className="relative mt-4">
        <div
          ref={scrollRef}
          className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 pl-1 pr-12 [-ms-overflow-style:auto] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-[#cbd5e1] [&::-webkit-scrollbar-track]:rounded-full [&::-webkit-scrollbar-track]:bg-[#eef2f7]"
          role="region"
          aria-label="Recent clinical reviews carousel"
        >
          {reviews.map((review) => {
            const style = REVIEW_ASSESSMENT_STYLES[review.assessment_key ?? "reviewed"] ?? REVIEW_ASSESSMENT_STYLES.reviewed;
            const Icon = style.icon;

            return (
              <article
                key={review.note_id}
                className="flex w-[min(100%,320px)] shrink-0 snap-start flex-col rounded-2xl border border-[#e8eef5] bg-white p-4 shadow-sm transition hover:border-[#cbd5e1] hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link
                      href={`/children/${review.child_id}?from=dashboard&focus=review`}
                      className="inline-flex max-w-full flex-wrap items-baseline gap-x-2 text-[#2563eb] hover:underline"
                    >
                      <span className="truncate text-base font-semibold">
                        {review.full_name?.trim() || review.pseudonymous_id || review.child_id}
                      </span>
                      {review.full_name?.trim() && review.pseudonymous_id ? (
                        <span className="text-xs font-medium text-[#64748b] no-underline">{review.pseudonymous_id}</span>
                      ) : null}
                    </Link>
                    <p className="mt-1 text-xs text-[#64748b]">{formatReviewWhen(review.created_at)}</p>
                  </div>
                  <span
                    className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${style.tone}`}
                  >
                    <Icon className="h-3 w-3" aria-hidden />
                    {review.assessment}
                  </span>
                </div>

                {review.workflow ? (
                  <p className="mt-3 text-xs text-[#475569]">
                    <span className="font-semibold text-[#0f2744]">Next step:</span> {review.workflow}
                  </p>
                ) : null}

                {review.note_excerpt ? (
                  <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-[#475569]">&ldquo;{review.note_excerpt}&rdquo;</p>
                ) : null}

                <div className="mt-auto flex items-center justify-between gap-2 border-t border-[#e8eef5] pt-3">
                  <p className="flex min-w-0 items-center gap-1.5 truncate text-xs text-[#64748b]">
                    <Stethoscope className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    <span className="truncate">{review.reviewer_name ?? "Clinician"}</span>
                  </p>
                  <Link
                    href={`/children/${review.child_id}?from=dashboard&focus=review`}
                    className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-[#2563eb] hover:underline"
                  >
                    Open
                    <ArrowRight className="h-3 w-3" aria-hidden />
                  </Link>
                </div>
              </article>
            );
          })}
        </div>

        {reviews.length > 1 ? (
          <>
            <button
              type="button"
              onClick={() => scrollByCard(-1)}
              className="absolute left-0 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-[#e8eef5] bg-white text-[#475569] shadow-md transition hover:border-[#cbd5e1] hover:text-[#0f2744]"
              aria-label="Previous clinical review"
            >
              <ChevronLeft className="h-5 w-5" aria-hidden />
            </button>
            <button
              type="button"
              onClick={() => scrollByCard(1)}
              className="absolute right-0 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-[#e8eef5] bg-white text-[#475569] shadow-md transition hover:border-[#cbd5e1] hover:text-[#0f2744]"
              aria-label="Next clinical review"
            >
              <ChevronRight className="h-5 w-5" aria-hidden />
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
}

function PriorityPatientRow({ row }: { row: PriorityPatient }) {
  const delta = row.probability_delta_pp;
  const DeltaIcon = delta == null ? Minus : delta > 0 ? ArrowUpRight : delta < 0 ? ArrowDownRight : Minus;
  const deltaTone =
    delta == null ? "text-[#64748b]" : delta > 0 ? "text-[#dc2626]" : delta < 0 ? "text-[#059669]" : "text-[#64748b]";

  const progressTooltip = [
    row.previous_probability != null ? `Previous assessment: ${formatPercent(row.previous_probability)}` : null,
    row.current_probability != null ? `Current: ${formatPercent(row.current_probability)}` : null,
    row.risk_velocity != null ? `Risk trend: ${formatRiskVelocity(row.risk_velocity)}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <article className="overflow-hidden rounded-2xl border border-[#e4ecf4] bg-white shadow-[0_1px_2px_rgba(10,39,72,0.04)] transition hover:shadow-[0_16px_40px_-28px_rgba(10,39,72,0.45)]">
      <div className="flex items-center justify-between gap-4 px-5 py-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Link
              href={`/children/${row.child_id}?from=dashboard&focus=review`}
              className="inline-flex max-w-full flex-wrap items-baseline gap-x-2 text-[#0f2744] hover:text-[#2563eb]"
            >
              <span className="truncate text-lg font-semibold tracking-tight">
                {row.full_name?.trim() || row.pseudonymous_id}
              </span>
              {row.full_name?.trim() ? (
                <span className="text-xs font-medium text-[#64748b]">{row.pseudonymous_id}</span>
              ) : null}
            </Link>
            <span className="text-sm text-[#64748b]">
              {ageLabel(row.age_months)}
              {row.sex ? ` · ${formatStatus(row.sex)}` : ""}
            </span>
            <ReviewBadge status={row.review_status} />
          </div>
          {row.current_status ? (
            <p className="mt-2 inline-flex rounded-full bg-[#f1f5f9] px-2.5 py-0.5 text-xs font-semibold text-[#0f2744]">
              {row.score_kind === "highest_condition_probability"
                ? `Predicted type: ${displayedMalnutritionType(row) || "—"}`
                : formatNutritionalStatus(displayedMalnutritionType(row), row.severity)}
            </p>
          ) : null}
        </div>
        <Link href={`/children/${row.child_id}?from=dashboard&focus=review`} className="shrink-0">
          <Button className="h-10 rounded-xl bg-[#0E3A67] px-4 text-sm hover:bg-[#0A2748]">
            Review Patient
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-2 divide-x divide-y divide-[#e8eef5] border-t border-[#e8eef5] bg-[#f8fafc] sm:grid-cols-4 sm:divide-y-0">
        <MetricCell label="Latest assessment">
          {row.latest_visit ? (
            new Date(row.latest_visit).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
          ) : (
            <span className="text-amber-700">Visit date unavailable</span>
          )}
        </MetricCell>

        <MetricCell
          label={
            <span className="inline-flex items-center gap-1">
              {row.probability_label}
              <ProbabilityInfoButton
                current={row.current_probability}
                previous={row.previous_probability}
                deltaPp={row.probability_delta_pp}
                twelveMonthRisk={row.score_kind === "highest_condition_probability"}
              />
            </span>
          }
        >
          <span className="text-xl font-semibold tabular-nums tracking-tight">{formatPercent(row.current_probability)}</span>
          {row.previous_probability != null ? (
            <span className="block text-xs text-[#64748b]">{formatPercent(row.previous_probability)} previous</span>
          ) : null}
        </MetricCell>

        <MetricCell
          label={
            <span className="inline-flex items-center gap-1">
              Change
              <ChangeInfoButton
                current={row.current_probability}
                previous={row.previous_probability}
                deltaPp={row.probability_delta_pp}
                riskVelocity={row.risk_velocity}
              />
            </span>
          }
        >
          {delta != null ? (
            <span className={`inline-flex items-center gap-1 font-medium ${deltaTone}`}>
              <DeltaIcon className="h-3.5 w-3.5" aria-hidden />
              {formatDeltaPp(delta)}
            </span>
          ) : (
            <span className="text-[#64748b]">Not available</span>
          )}
          {row.risk_velocity != null ? (
            <span className="mt-0.5 block text-xs text-[#64748b]">
              Risk trend: {formatRiskVelocity(row.risk_velocity)}
            </span>
          ) : null}
        </MetricCell>

        <MetricCell label="Progress">
          <span title={progressTooltip || undefined}>
            <StatusBadge value={row.progress_state ?? "unknown"} />
          </span>
        </MetricCell>
      </div>
    </article>
  );
}

function ChangeInfoButton({
  current,
  previous,
  deltaPp,
  riskVelocity,
}: {
  current?: number | null;
  previous?: number | null;
  deltaPp?: number | null;
  riskVelocity?: number | null;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const hasDelta = deltaPp != null && previous != null && current != null;
  const hasTrend = riskVelocity != null;

  return (
    <div className="relative inline-flex" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="rounded-full p-0.5 text-[#94a3b8] hover:bg-[#eef2f7] hover:text-[#64748b]"
        aria-label="What does this change mean?"
        aria-expanded={open}
      >
        <Info className="h-3 w-3" aria-hidden />
      </button>
      {open ? (
        <div
          role="tooltip"
          className="absolute left-0 top-full z-30 mt-1.5 w-72 rounded-xl border border-[#e8eef5] bg-white p-3 text-left text-xs leading-relaxed text-[#475569] shadow-lg"
        >
          <p className="font-semibold text-[#0f2744]">For this child</p>
          {!hasDelta && !hasTrend ? (
            <p className="mt-2">Change is not available yet. At least two visits are needed to compare.</p>
          ) : (
            <>
              {hasDelta ? (
                <p className="mt-2">
                  Risk moved from <strong className="text-[#0f2744]">{formatPercent(previous)}</strong> to{" "}
                  <strong className="text-[#0f2744]">{formatPercent(current)}</strong>
                  {deltaPp === 0
                    ? " — no change since the last visit."
                    : deltaPp! > 0
                      ? ` — up ${deltaPp} pp since the last visit.`
                      : ` — down ${Math.abs(deltaPp!)} pp since the last visit.`}
                </p>
              ) : null}
              {hasTrend ? (
                <p className="mt-2">
                  Risk trend is <strong className="text-[#0f2744]">{formatRiskVelocity(riskVelocity)}</strong>, based
                  on the time between visits.
                </p>
              ) : null}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}

function ProbabilityInfoButton({
  current,
  previous,
  deltaPp,
  twelveMonthRisk = false,
}: {
  current?: number | null;
  previous?: number | null;
  deltaPp?: number | null;
  twelveMonthRisk?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const currentText = formatPercent(current);
  const previousText = formatPercent(previous);

  let changeText: string | null = null;
  if (deltaPp != null && previous != null && current != null) {
    if (deltaPp > 0) changeText = `Risk has increased by ${deltaPp} percentage points since the last visit.`;
    else if (deltaPp < 0) changeText = `Risk has decreased by ${Math.abs(deltaPp)} percentage points since the last visit.`;
    else changeText = "Risk is unchanged since the last visit.";
  }

  return (
    <div className="relative inline-flex" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="rounded-full p-0.5 text-[#94a3b8] hover:bg-[#eef2f7] hover:text-[#64748b]"
        aria-label="What does this percentage mean?"
        aria-expanded={open}
      >
        <Info className="h-3 w-3" aria-hidden />
      </button>
      {open ? (
        <div
          role="tooltip"
          className="absolute left-0 top-full z-30 mt-1.5 w-72 rounded-xl border border-[#e8eef5] bg-white p-3 text-left text-xs leading-relaxed text-[#475569] shadow-lg"
        >
          <p className="font-semibold text-[#0f2744]">For this child</p>
          {current == null ? (
            <p className="mt-2">No model probability is available from the latest visit yet.</p>
          ) : (
            <>
              <p className="mt-2">
                {twelveMonthRisk
                  ? "This is the highest GA-RGCA v3 condition probability. It is a model estimate, not a confirmed current nutritional status."
                  : "The model currently estimates nutritional risk from the latest visit."}{" "}
                <strong className="text-[#0f2744]">{currentText}</strong>
              </p>
              {previous != null ? (
                <>
                  <p className="mt-2">
                    At the previous visit, it was <strong className="text-[#0f2744]">{previousText}</strong>.
                  </p>
                  {changeText ? <p className="mt-2">{changeText}</p> : null}
                </>
              ) : (
                <p className="mt-2">There is no earlier visit to compare yet.</p>
              )}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}

function MetricCell({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <div className="bg-white px-5 py-3.5">
      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#94a3b8]">{label}</div>
      <div className="mt-1.5 text-sm text-[#0f2744]">{children}</div>
    </div>
  );
}

function ReviewBadge({ status }: { status: string }) {
  const label = REVIEW_LABELS[status] ?? formatStatus(status);
  const tone =
    status === "AWAITING_REVIEW"
      ? "bg-amber-50 text-amber-800 border-amber-200"
      : status === "REVIEWED"
        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
        : "bg-slate-50 text-slate-700 border-slate-200";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${tone}`}>
      {label}
    </span>
  );
}

function SummaryTile({
  label,
  value,
  href,
  onClick,
  accent,
  icon: Icon,
  selected,
}: {
  label: string;
  value: number;
  href?: string;
  onClick?: () => void;
  accent?: "amber" | "red";
  icon: LucideIcon;
  selected?: boolean;
}) {
  const iconTone =
    accent === "red"
      ? "bg-[#fee2e2] text-[#dc2626]"
      : accent === "amber"
        ? "bg-[#fef3c7] text-[#d97706]"
        : "bg-[#eaf2fa] text-[#2563eb]";

  const inner = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-[#64748b]">{label}</p>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${iconTone}`}>
          <Icon className="h-[18px] w-[18px]" strokeWidth={2} aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-3xl font-semibold tabular-nums text-[#0f2744]">{value}</p>
    </>
  );

  const className = `w-full rounded-3xl bg-white p-4 text-left shadow-[0_4px_24px_rgba(15,40,80,0.06)] transition hover:shadow-[0_8px_32px_rgba(15,40,80,0.08)] ${
    selected ? "ring-2 ring-[#2563eb] ring-offset-1" : ""
  }`;

  if (href) {
    return (
      <Link href={href} className={`block ${className}`}>
        {inner}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {inner}
      </button>
    );
  }

  return <div className={className}>{inner}</div>;
}

function FollowUpWorklistSection({
  followUps,
}: {
  followUps: Dashboard["follow_ups"];
}) {
  const hasOverdue = followUps.overdue.length > 0;
  const hasToday = followUps.today.length > 0;

  return (
    <section className="flex h-full flex-col rounded-3xl bg-white p-5 shadow-[0_4px_24px_rgba(15,40,80,0.06)]">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#eaf2fa] text-[#0E3A67]">
            <CalendarClock className="h-4 w-4" />
          </span>
          <h2 className="text-base font-semibold text-[#0f2744]">Follow-Up Worklist</h2>
        </div>
        {followUps.total_scheduled === 0 ? null : (
          <Link href="/visits" className="shrink-0 text-sm font-medium text-[#2563eb] hover:underline">
            View all follow-ups →
          </Link>
        )}
      </div>

      <div className="mt-4 min-h-0 flex-1 overflow-y-auto pr-1 [scrollbar-width:thin] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-[#cbd5e1] [&::-webkit-scrollbar-track]:rounded-full [&::-webkit-scrollbar-track]:bg-[#eef2f7]">
      {hasOverdue ? (
        <div>
          <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#dc2626]">
            <AlertTriangle className="h-3.5 w-3.5" />
            Overdue
          </p>
          <ul className="mt-2 space-y-2">
            {followUps.overdue.map((f) => (
              <FollowUpRow key={`${f.child_id}-${f.date}`} item={f} urgent />
            ))}
          </ul>
        </div>
      ) : null}

      {hasToday ? (
        <div className={hasOverdue ? "mt-5 border-t border-[#e8eef5] pt-4" : ""}>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#2563eb]">Today</p>
          <ul className="mt-2 space-y-2">
            {followUps.today.map((f) => (
              <FollowUpRow key={`${f.child_id}-${f.date}`} item={f} />
            ))}
          </ul>
        </div>
      ) : null}

      {followUps.upcoming.length > 0 ? (
        <div className={hasOverdue || hasToday ? "mt-5 border-t border-[#e8eef5] pt-4" : ""}>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">Upcoming</p>
          <ul className="mt-2 space-y-2">
            {followUps.upcoming.map((f) => (
              <FollowUpRow key={`${f.child_id}-${f.date}`} item={f} />
            ))}
          </ul>
        </div>
      ) : null}

      {followUps.total_scheduled === 0 ? (
        <p className="rounded-2xl bg-[#f8fafc] px-4 py-6 text-center text-sm text-[#64748b]">No follow-ups scheduled.</p>
      ) : null}
      </div>
    </section>
  );
}

function followUpDateParts(value: string) {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  const date = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return {
    day: date.toLocaleDateString(undefined, { day: "numeric" }),
    month: date.toLocaleDateString(undefined, { month: "short" }),
  };
}

function FollowUpRow({ item, urgent = false }: { item: FollowUpItem; urgent?: boolean }) {
  const when = followUpDateParts(item.date);
  return (
    <li>
      <Link
        href={`/children/${item.child_id}?from=dashboard&focus=followup`}
        className={`group flex items-center gap-3 rounded-2xl border px-3 py-2.5 transition ${
          urgent
            ? "border-red-100 bg-red-50 hover:bg-white"
            : "border-[#e8eef5] bg-[#f8fafc] hover:border-[#d5dee8] hover:bg-white"
        }`}
      >
        <span
          className={`flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-xl bg-white ring-1 ${
            urgent ? "text-[#991b1b] ring-red-100" : "text-[#0f2744] ring-[#e4ecf4]"
          }`}
        >
          <span className={`text-[10px] font-semibold uppercase tracking-wide ${urgent ? "text-[#dc2626]" : "text-[#64748b]"}`}>
            {when?.month ?? "—"}
          </span>
          <span className="text-base font-semibold leading-none">{when?.day ?? "—"}</span>
        </span>
        <span className="min-w-0 flex-1">
          <span className={`flex min-w-0 items-baseline gap-x-2 ${urgent ? "text-[#991b1b]" : "text-[#0f2744]"}`}>
            <span className="truncate text-sm font-semibold">{item.full_name?.trim() || item.child}</span>
            {item.full_name?.trim() && item.child ? (
              <span className="shrink-0 text-[11px] font-medium text-[#64748b]">{item.child}</span>
            ) : null}
          </span>
          <span className="mt-0.5 block truncate text-xs text-[#64748b]">
            {urgent && item.overdue_days != null ? `Overdue by ${item.overdue_days} days · ` : ""}
            {item.clinic}
          </span>
        </span>
        <ChevronRight className="h-4 w-4 shrink-0 text-[#94a3b8] transition group-hover:text-[#0f2744]" aria-hidden />
      </Link>
    </li>
  );
}

function renderProgressSliceLabel({
  cx = 0,
  cy = 0,
  midAngle = 0,
  outerRadius = 0,
  pct = 0,
}: {
  cx?: number;
  cy?: number;
  midAngle?: number;
  outerRadius?: number;
  pct?: number;
}) {
  if (pct < 10) return null;
  const RADIAN = Math.PI / 180;
  const radius = outerRadius * 0.62;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="#fff" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {pct}%
    </text>
  );
}

function ProgressOverviewSection({
  items,
  pieData,
  total,
}: {
  items: { name: string; n: number; fill: string; pct: number }[];
  pieData: { name: string; n: number; fill: string; pct: number }[];
  total: number;
}) {
  return (
    <section className="overflow-hidden rounded-3xl border border-[#e8eef5] bg-gradient-to-br from-white via-white to-[#f0f6fc] p-5 shadow-[0_4px_24px_rgba(15,40,80,0.06)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-[#0f2744]">Longitudinal Progress Overview</h2>
          <p className="mt-1 text-xs text-[#64748b]">
            How your monitored children are progressing across repeat visits
          </p>
        </div>
        <div className="shrink-0 rounded-full border border-[#e8eef5] bg-white px-3 py-1.5 text-center">
          <p className="text-xl font-semibold tabular-nums leading-none text-[#0f2744]">{total}</p>
          <p className="mt-0.5 text-[10px] text-[#64748b]">tracked</p>
        </div>
      </div>

      {total === 0 ? (
        <div className="mt-6 rounded-2xl border border-dashed border-[#dbe4ef] bg-white/70 px-6 py-10 text-center">
          <p className="text-sm font-medium text-[#475569]">No progress data yet</p>
          <p className="mt-1 text-xs text-[#64748b]">Progress states appear after repeat assessments.</p>
        </div>
      ) : (
        <div className="mt-5 flex flex-col items-center">
          <div className="h-[280px] w-full max-w-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="n"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={118}
                  paddingAngle={pieData.length > 1 ? 2 : 0}
                  stroke="#fff"
                  strokeWidth={2}
                  label={(props) =>
                    renderProgressSliceLabel({
                      cx: props.cx,
                      cy: props.cy,
                      midAngle: props.midAngle,
                      outerRadius: props.outerRadius,
                      pct: (props.payload as { pct?: number })?.pct,
                    })
                  }
                  labelLine={false}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const row = payload[0].payload as (typeof pieData)[number];
                    return (
                      <div className="rounded-xl border border-[#e8eef5] bg-white px-3 py-2 text-xs shadow-lg">
                        <p className="font-semibold text-[#0f2744]">{row.name}</p>
                        <p className="mt-0.5 text-[#64748b]">
                          {row.n} children · {row.pct}%
                        </p>
                      </div>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 flex w-full flex-wrap justify-center gap-2">
            {items.map((item) => (
              <div
                key={item.name}
                className="inline-flex items-center gap-2 rounded-full border border-[#e8eef5] bg-white px-3 py-1.5 text-xs text-[#475569]"
              >
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: item.fill }} />
                <span className="font-medium text-[#0f2744]">{item.name}</span>
                <span className="font-semibold tabular-nums text-[#0f2744]">{item.n}</span>
                <span className="tabular-nums text-[#64748b]">({item.pct}%)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
