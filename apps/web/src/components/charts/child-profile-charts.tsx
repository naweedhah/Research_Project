"use client";

import { useId, useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendPoint } from "@/data/child-profile";
import { cn, formatClinicalDate, formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";

type Point = TrendPoint;
export type TrendMetric = "probability" | "weight" | "height";

const METRIC: Record<TrendMetric, { key: keyof Point; label: string; unit: string; color: string; yDomain?: [number, number] }> = {
  probability: { key: "probability", label: "Model-assessed probability", unit: "%", color: "#2563eb", yDomain: [0, 100] },
  weight: { key: "weight", label: "Weight", unit: "kg", color: "#0f766e" },
  height: { key: "height", label: "Height", unit: "cm", color: "#0ea5e9" },
};

export function TrendChart({
  data,
  metric,
  comparable,
  scoreLabel,
}: {
  data: Point[];
  metric: TrendMetric;
  comparable: boolean;
  scoreLabel?: string;
}) {
  const base = METRIC[metric];
  const spec =
    metric === "probability" && scoreLabel
      ? { ...base, label: scoreLabel }
      : base;
  const series = useMemo(
    () => data.filter((d) => d[spec.key] != null).map((d) => ({ ...d, value: d[spec.key] as number })),
    [data, spec.key],
  );

  if (!comparable && metric === "probability") {
    return (
      <p className="rounded-xl bg-amber-50 px-4 py-6 text-sm text-amber-950">
        Longitudinal comparison unavailable. The active model changed between these assessments.
      </p>
    );
  }

  if (series.length < 2) {
    return (
      <p className="rounded-xl bg-[#f8fafc] px-4 py-6 text-sm text-[#64748b]">
        Insufficient history. Available after the next completed assessment.
      </p>
    );
  }

  return (
    <div className="h-56 w-full rounded-xl bg-[#f8fafc] px-1 py-2 ring-1 ring-line/70" role="img" aria-label={`${spec.label} over visits`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#e8eef5" strokeDasharray="3 3" />
          <XAxis dataKey="visit" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
          <YAxis
            domain={spec.yDomain ?? ["auto", "auto"]}
            tick={{ fontSize: 12, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
            width={44}
            tickFormatter={(v) => (metric === "probability" ? `${v}` : String(v))}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const row = payload[0].payload as Point & { value: number };
              return (
                <div className="rounded-xl border border-line bg-white px-3 py-2 text-xs shadow-card">
                  <p className="font-semibold text-[#0f2744]">
                    {row.visit} · {formatClinicalDate(row.date)}
                  </p>
                  {metric === "probability" ? (
                    <>
                      <p className="mt-1 text-[#64748b]">Status: {formatNutritionalStatus(row.status, row.severity)}</p>
                      <p className="text-[#64748b]">Severity: {formatStatus(row.severity)}</p>
                      <p className="font-medium text-[#0f2744]">
                        {spec.label}: {formatPercent((row.probability ?? 0) / 100)}
                      </p>
                    </>
                  ) : (
                    <p className="mt-1 font-medium text-[#0f2744]">
                      {spec.label}: {row.value} {spec.unit}
                    </p>
                  )}
                </div>
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={spec.color}
            strokeWidth={2.5}
            dot={{ r: 5, fill: spec.color, stroke: "#fff", strokeWidth: 2 }}
            activeDot={{ r: 6 }}
            isAnimationActive
            animationDuration={600}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LatentTrajectory({
  visits,
  warning,
  compact = false,
  className,
}: {
  visits: { id: string; visit_number: number; visit_date: string; projection?: { x: number; y: number } | null; prediction?: { risk?: number; status?: string } | null }[];
  warning?: string | null;
  compact?: boolean;
  className?: string;
}) {
  const uid = useId().replace(/:/g, "");
  const gridId = `latent-grid-${uid}`;
  const arrowId = `latent-arrow-${uid}`;
  const pts = visits.filter((v) => v.projection);
  if (pts.length === 0) {
    return (
      <p className={cn("rounded-xl bg-[#f8fafc] px-4 text-sm text-[#64748b]", compact ? "py-4" : "py-6")}>
        Projection coordinates appear after a visit produces a stored embedding.
      </p>
    );
  }
  const xs = pts.map((p) => p.projection!.x);
  const ys = pts.map((p) => p.projection!.y);
  const minX = Math.min(...xs, -1);
  const maxX = Math.max(...xs, 1);
  const minY = Math.min(...ys, -1);
  const maxY = Math.max(...ys, 1);
  const height = compact ? 180 : 300;
  const plotBottom = compact ? 150 : 260;
  const plotSpan = compact ? 120 : 200;
  const sx = (x: number) => ((x - minX) / (maxX - minX || 1)) * 520 + 40;
  const sy = (y: number) => plotBottom - ((y - minY) / (maxY - minY || 1)) * plotSpan;

  return (
    <div className={className}>
      {warning ? <p className="mb-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-950">{warning}</p> : null}
      <svg
        viewBox={`0 0 600 ${height}`}
        className={cn("w-full rounded-xl bg-[#f8fafc] ring-1 ring-line/70", compact && "max-h-40")}
        role="img"
        aria-label="Latent representation trajectory"
      >
        <defs>
          <pattern id={gridId} width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" fill="#94a3b8" opacity="0.35" />
          </pattern>
          <marker id={arrowId} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#2563eb" />
          </marker>
        </defs>
        <rect width="600" height={height} fill={`url(#${gridId})`} />
        {pts.map((p, i) => {
          const x = sx(p.projection!.x);
          const y = sy(p.projection!.y);
          const next = pts[i + 1];
          return (
            <g key={p.id}>
              {next ? (
                <line
                  x1={x}
                  y1={y}
                  x2={sx(next.projection!.x)}
                  y2={sy(next.projection!.y)}
                  stroke="#2563eb"
                  strokeWidth="2"
                  markerEnd={`url(#${arrowId})`}
                />
              ) : null}
              <circle cx={x} cy={y} r={compact ? 5 : 7} fill="#2563eb">
                <title>{`V${p.visit_number} · ${formatClinicalDate(p.visit_date)}`}</title>
              </circle>
              <text x={x + 8} y={y - 6} fontSize={compact ? "10" : "11"} fill="#0f2744">
                V{p.visit_number}
              </text>
            </g>
          );
        })}
      </svg>
      {!compact ? (
        <p className="mt-3 text-xs leading-relaxed text-[#64748b]">
          This visualization represents changes in the model&apos;s learned multidimensional representation. It does not
          independently determine clinical status.
        </p>
      ) : null}
    </div>
  );
}
