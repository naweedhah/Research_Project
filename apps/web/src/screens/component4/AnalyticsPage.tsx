"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CurrentFutureDistribution } from "@/components/clinical/current-future-distribution";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";
import { useClinicChildren } from "@/data/use-clinic-children";
import { formatStatus } from "@/utils/utils";

type Dashboard = {
  risk_trend: { improving: number; stable: number; stagnating: number; deteriorating: number; insufficient_history: number; total_classified: number };
  kpis: { children_under_monitoring: number; awaiting_clinical_review: number; open_alerts: number; overdue_follow_ups: number };
};

const AGE_BANDS: [string, number, number][] = [
  ["0–5 mo", 0, 5],
  ["6–11 mo", 6, 11],
  ["12–23 mo", 12, 23],
  ["24–35 mo", 24, 35],
  ["36–47 mo", 36, 47],
  ["48–60 mo", 48, 60],
];

const TICK = { fill: "#5C6E82", fontSize: 12 };

export default function AnalyticsPage() {
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/dashboard") });
  const children = useClinicChildren();

  const progressChart = useMemo(() => {
    const t = dashboard.data?.risk_trend;
    if (!t) return [];
    return [
      { name: "Improving", n: t.improving },
      { name: "Stable", n: t.stable },
      { name: "Stagnating", n: t.stagnating },
      { name: "Deteriorating", n: t.deteriorating },
      { name: "Insufficient history", n: t.insufficient_history },
    ];
  }, [dashboard.data]);

  const ageChart = useMemo(() => {
    const rows = children.data ?? [];
    return AGE_BANDS.map(([name, lo, hi]) => ({ name, n: rows.filter((c) => c.age_months >= lo && c.age_months <= hi).length }));
  }, [children.data]);

  const visitActivity = useMemo(() => {
    const rows = children.data ?? [];
    const withVisit = rows.filter((c) => c.last_visit).length;
    const now = Date.now();
    const last30 = rows.filter((c) => c.last_visit && now - new Date(c.last_visit).getTime() <= 30 * 86400000).length;
    const last90 = rows.filter((c) => c.last_visit && now - new Date(c.last_visit).getTime() <= 90 * 86400000).length;
    return { total: rows.length, withVisit, last30, last90 };
  }, [children.data]);

  if (dashboard.isError) return <ErrorState message={dashboard.error instanceof Error ? dashboard.error.message : "Analytics could not be loaded."} />;

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#3E75B8]">Facility analytics</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[#102A4C]">Analytics</h1>
        <p className="mt-1 text-sm text-[#5C6E82]">Facility-level view of the current nutritional profile and the predicted 12-month risk. Current and future are never merged.</p>
      </header>

      {dashboard.isLoading ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4" aria-busy="true">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-[24px]" />
          ))}
        </div>
      ) : (
        <section className="grid grid-cols-2 gap-3 md:grid-cols-4" aria-label="Key figures">
          {[
            ["Children monitored", dashboard.data?.kpis.children_under_monitoring ?? 0],
            ["Awaiting review", dashboard.data?.kpis.awaiting_clinical_review ?? 0],
            ["Open alerts", dashboard.data?.kpis.open_alerts ?? 0],
            ["Overdue follow-ups", dashboard.data?.kpis.overdue_follow_ups ?? 0],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-[24px] border border-white/80 bg-white/85 p-4 shadow-card backdrop-blur-xl">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#5C6E82]">{label}</p>
              <p className="mt-2 text-3xl font-semibold tabular-nums text-[#102A4C]">{value}</p>
            </div>
          ))}
        </section>
      )}

      <section>
        <h2 className="mb-3 text-base font-semibold text-[#102A4C]">Current nutritional profile vs predicted 12-month risk</h2>
        {children.isError ? (
          <ErrorState message={children.error instanceof Error ? children.error.message : "Child list could not be loaded."} />
        ) : (
          <CurrentFutureDistribution rows={children.data} loading={children.isLoading} />
        )}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-[24px] border border-white/80 bg-white/85 p-5 shadow-card backdrop-blur-xl">
          <h2 className="text-base font-semibold text-[#102A4C]">Longitudinal progress</h2>
          <p className="text-xs text-[#5C6E82]">Children classified by change in predicted risk across repeat visits.</p>
          <div className="mt-4 h-64">
            {progressChart.length === 0 ? (
              <EmptyState title="No progress data yet." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={progressChart}>
                  <XAxis dataKey="name" tick={TICK} axisLine={false} tickLine={false} interval={0} />
                  <YAxis allowDecimals={false} tick={TICK} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "rgba(16,42,76,0.06)" }} />
                  <Bar dataKey="n" fill="#346FA7" radius={[10, 10, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
        <div className="rounded-[24px] border border-white/80 bg-white/85 p-5 shadow-card backdrop-blur-xl">
          <h2 className="text-base font-semibold text-[#102A4C]">Age distribution</h2>
          <p className="text-xs text-[#5C6E82]">Registered children by age band (months).</p>
          <div className="mt-4 h-64">
            {children.isLoading ? (
              <Skeleton className="h-full" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ageChart}>
                  <XAxis dataKey="name" tick={TICK} axisLine={false} tickLine={false} interval={0} />
                  <YAxis allowDecimals={false} tick={TICK} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "rgba(16,42,76,0.06)" }} />
                  <Bar dataKey="n" fill="#45C4BB" radius={[10, 10, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-[24px] border border-white/80 bg-white/85 p-5 shadow-card backdrop-blur-xl">
        <h2 className="text-base font-semibold text-[#102A4C]">Visit activity</h2>
        <p className="text-xs text-[#5C6E82]">Based on the latest recorded visit date for each child.</p>
        <dl className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            ["Registered", visitActivity.total],
            ["With a recorded visit", visitActivity.withVisit],
            ["Seen in last 30 days", visitActivity.last30],
            ["Seen in last 90 days", visitActivity.last90],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-2xl bg-[#F4F7FA] px-4 py-3">
              <dt className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#5C6E82]">{formatStatus(String(label))}</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums text-[#102A4C]">{children.isLoading ? "…" : value}</dd>
            </div>
          ))}
        </dl>
      </section>
      <p className="text-xs text-[#5C6E82]">Research decision-support prototype. Clinician confirmation required. Figures are computed from stored records only.</p>
    </div>
  );
}
