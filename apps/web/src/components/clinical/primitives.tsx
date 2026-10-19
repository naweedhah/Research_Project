"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { cn } from "@/utils/utils";

export function ClinicalPageHeader({
  kicker,
  title,
  subtitle,
  action,
}: {
  kicker?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {kicker ? <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#3E75B8]">{kicker}</p> : null}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#102A4C] sm:text-[1.75rem]">{title}</h1>
        {subtitle ? <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[#5C6E82]">{subtitle}</p> : null}
      </div>
      {action}
    </header>
  );
}

export function ClinicalSurface({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section className={cn("rounded-[24px] border border-white/80 bg-white/80 p-5 shadow-card backdrop-blur-xl", className)}>
      {children}
    </section>
  );
}

export function DarkIntelligencePanel({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section
      className={cn(
        "rounded-[24px] border border-white/10 bg-[#102A4C] p-5 text-white shadow-elevated",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function CurrentFutureComparison({
  currentLabel,
  futureLabel,
}: {
  currentLabel: string;
  futureLabel: string;
}) {
  const reduce = useReducedMotion();
  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/80 bg-white/75 p-5 shadow-card backdrop-blur-xl">
      <div className="pointer-events-none absolute inset-x-[18%] top-1/2 hidden h-px bg-gradient-to-r from-transparent via-[#45C4BB] to-[#102A4C] md:block" aria-hidden />
      <div className="relative grid items-center gap-3 md:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-2xl bg-white/80 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5C6E82]">Current WHO assessment</p>
          <p className="mt-1 text-lg font-semibold text-[#102A4C]">{currentLabel}</p>
          <p className="mt-0.5 text-[11px] text-[#5C6E82]">Based on latest recorded anthropometric measurements</p>
        </div>
        <div className="flex items-center justify-center text-[#45C4BB]" aria-hidden>
          <motion.span
            className="text-2xl"
            animate={reduce ? undefined : { x: [0, 6, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          >
            →
          </motion.span>
        </div>
        <div className="rounded-2xl bg-[#0E243D] px-4 py-3 text-white">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#58D3CA]">Next 12 months · AI prediction</p>
          <p className="mt-1 text-lg font-semibold">{futureLabel}</p>
          <p className="mt-0.5 text-[11px] text-white/70">GA-RGCA-v4-Rolling-RSL · clinician confirmation required</p>
        </div>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-[#5C6E82]">
        The current assessment describes the child today. The prediction describes nutritional risk over the next 12 months. They are different time points and must not be read as one status.
      </p>
    </div>
  );
}

export function ProbabilityBar({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | null | undefined;
  tone: "gold" | "amber" | "orange" | "coral";
}) {
  const width = value == null ? 0 : Math.max(0, Math.min(100, value <= 1 ? value * 100 : value));
  const color = {
    gold: "#C4A15A",
    amber: "#E8AE4E",
    orange: "#E08A3C",
    coral: "#EA6B60",
  }[tone];
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span>{label}</span>
        <span className="tabular-nums">{value == null ? "—" : `${Math.round(width)}%`}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/15" role="img" aria-label={`${label} ${Math.round(width)} percent`}>
        <div className="h-full rounded-full" style={{ width: `${width}%`, background: color }} />
      </div>
    </div>
  );
}
