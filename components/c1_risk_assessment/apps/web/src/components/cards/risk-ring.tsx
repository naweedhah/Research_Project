"use client";

import { cn } from "@/utils/utils";

export function RiskRing({ value, label = "Current Risk" }: { value?: number | null; label?: string }) {
  const pct = Math.round((value ?? 0) * 100);
  const r = 36;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const tone = pct >= 70 ? "#B91C1C" : pct >= 50 ? "#B45309" : "#047857";
  return (
    <div className="flex flex-col items-center">
      <svg width="96" height="96" viewBox="0 0 96 96" role="img" aria-label={`${pct} percent ${label}`}>
        <circle cx="48" cy="48" r={r} fill="none" stroke="#E4E0D8" strokeWidth="8" />
        <circle
          cx="48"
          cy="48"
          r={r}
          fill="none"
          stroke={tone}
          strokeWidth="8"
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 48 48)"
        />
        <text x="48" y="52" textAnchor="middle" className="fill-ink" fontSize="18" fontWeight="600">
          {value == null ? "—" : `${pct}%`}
        </text>
      </svg>
      <p className="mt-1 text-xs uppercase tracking-wide text-muted">{label}</p>
    </div>
  );
}
