"use client";

import { useMemo } from "react";
import { summarizeClinicBoard, type ClinicBoardPicture, type ClinicChildInput } from "@/data/clinic-board";
import { Skeleton } from "@/components/common/states";

function Slices({ slices, total, dark }: { slices: ClinicBoardPicture["measured"]; total: number; dark?: boolean }) {
  return (
    <ul className="mt-3 space-y-2">
      {slices.map((slice) => {
        const pct = total > 0 ? Math.round((slice.count / total) * 100) : 0;
        return (
          <li key={slice.key}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className={dark ? "text-white/85" : "text-[#102A4C]"}>{slice.label}</span>
              <span className={`tabular-nums ${dark ? "text-white/70" : "text-[#5C6E82]"}`}>
                {slice.count} · {pct}%
              </span>
            </div>
            <div className={`h-1.5 overflow-hidden rounded-full ${dark ? "bg-white/10" : "bg-[#E8EFF5]"}`}>
              <div className="h-full rounded-full transition-[width] duration-700" style={{ width: `${pct}%`, backgroundColor: slice.color }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Current WHO distribution vs 12-month prediction distribution for the facility.
 * Both are computed from the stored child list with the frozen WHO and display rules.
 */
export function CurrentFutureDistribution({ rows, loading }: { rows?: ClinicChildInput[]; loading?: boolean }) {
  const picture = useMemo(() => summarizeClinicBoard(rows ?? []), [rows]);
  if (loading) return <Skeleton className="h-64 rounded-[24px]" />;
  const total = picture.children;
  return (
    <section className="grid gap-4 md:grid-cols-2" aria-label="Current WHO distribution and future prediction distribution">
      <div className="rounded-[24px] border border-white/80 bg-white/85 p-5 shadow-card backdrop-blur-xl">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5C6E82]">Current · WHO assessment</p>
        <h3 className="mt-1 text-base font-semibold text-[#102A4C]">Latest recorded measurements</h3>
        <p className="text-xs text-[#5C6E82]">{total} children · WHO status from the latest visit</p>
        <Slices slices={picture.measured} total={total} />
      </div>
      <div className="rounded-[24px] bg-[#0E243D] p-5 text-white shadow-elevated">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#58D3CA]">Future · next 12 months</p>
        <h3 className="mt-1 text-base font-semibold">GA-RGCA-v4-Rolling-RSL prediction</h3>
        <p className="text-xs text-white/70">{total} children · predicted type from the latest visit</p>
        <Slices slices={picture.predicted} total={total} dark />
        <p className="mt-3 text-[11px] text-white/60">Prediction, not current status. Research decision-support prototype.</p>
      </div>
    </section>
  );
}
