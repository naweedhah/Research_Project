"use client";

import { forwardRef, type ReactNode, useLayoutEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/utils/utils";
import { formatPp, measurementDelta } from "@/data/child-profile";

type Chip = {
  id: string;
  label: string;
  value: string;
  hint?: string | null;
  secondaryLabel?: string | null;
  secondaryValue?: string | null;
  delta?: number | null;
  deltaKind?: "measurement" | "risk";
  unit?: string;
  history?: number[];
  side: "left" | "right";
  valueTestId?: string;
  labelTip?: string;
};

type LinkPath = { d: string; x: number; y: number };

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const w = 44;
  const h = 16;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / (max - min || 1)) * (h - 5) - 2.5;
    return { x, y };
  });
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const last = points[points.length - 1];
  return (
    <svg width={w} height={h} className="text-[#5b8ec8]" aria-hidden>
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last.x} cy={last.y} r="1.6" fill="currentColor" />
    </svg>
  );
}

function changeTone(delta: number, kind: "measurement" | "risk") {
  if (delta === 0) return "text-[#64748b]";
  if (kind === "risk") return delta > 0 ? "text-[#b91c1c]" : "text-[#047857]";
  return delta > 0 ? "text-[#047857]" : "text-[#b91c1c]";
}

function changeArrow(delta: number) {
  if (delta === 0) return "→";
  return delta > 0 ? "↑" : "↓";
}

function severityBadgeClass(value?: string | null) {
  const v = (value ?? "").toLowerCase();
  if (v.includes("severe")) return "bg-red-50 text-[#9f1239] ring-red-200/80";
  if (v.includes("moderate")) return "bg-amber-50 text-[#b45309] ring-amber-200/80";
  return "bg-slate-100 text-[#475569] ring-slate-200/80";
}

function ChildIdHeadTag({ childId }: { childId: string }) {
  return (
    <div className="relative z-[3] mb-2 flex shrink-0 justify-center">
      <div className="hud-id-plate" aria-label={`Child identifier ${childId}`}>
        <span className="hud-id-plate-mark" aria-hidden>
          ID
        </span>
        <span className="hud-id-plate-value">{childId}</span>
      </div>
    </div>
  );
}

const ChipCard = forwardRef<HTMLElement, { chip: Chip; delay: number; compact?: boolean }>(function ChipCard(
  { chip, delay, compact },
  ref,
) {
  const isStatus = chip.id === "status";
  const isAi = chip.id === "probability";
  const isProgress = chip.id === "progress";
  const isDate = chip.id === "visit";
  const prominent = !compact && (isStatus || isAi);

  return (
    <article
      ref={ref}
      data-testid={`measure-${chip.id}`}
      style={{ animationDelay: `${delay}ms` }}
      className={cn("hud-metric-card hud-chip", compact ? "min-h-[3.5rem]" : "min-h-[4.75rem]", isDate && "opacity-95")}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]" title={chip.labelTip}>
          {chip.label}
        </p>
        {!compact && chip.history ? <Sparkline values={chip.history} /> : null}
      </div>
      <p
        data-testid={chip.valueTestId}
        className={cn(
          "mt-1.5 font-semibold tabular-nums leading-tight text-navy-900",
          compact ? "text-[1.05rem]" : prominent ? "text-[1.35rem]" : isDate ? "text-[0.95rem]" : "text-[1.2rem]",
        )}
      >
        {chip.value}
      </p>
      {!compact && isStatus && chip.secondaryValue ? (
        <span className={cn("mt-2 inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold ring-1", severityBadgeClass(chip.secondaryValue))}>
          {chip.secondaryValue}
        </span>
      ) : null}
      {!compact && isProgress && chip.secondaryValue ? (
        <p className="mt-1.5 text-[12px] leading-snug text-[#64748b]">
          {chip.secondaryLabel} {chip.secondaryValue}
        </p>
      ) : null}
      {!compact && !isStatus && !isProgress && chip.hint ? (
        <p className="mt-1.5 text-[12px] leading-snug text-[#64748b]">
          {chip.hint}
          {chip.delta != null ? (
            <span className={cn("ml-1.5 font-semibold tabular-nums", changeTone(chip.delta, chip.deltaKind ?? "measurement"))}>
              {changeArrow(chip.delta)}{" "}
              {chip.deltaKind === "risk"
                ? formatPp(chip.delta)
                : `${Math.abs(chip.delta)} ${chip.unit ?? ""}`.trim()}
            </span>
          ) : null}
        </p>
      ) : !compact && !isStatus && !isProgress && chip.delta != null ? (
        <p className={cn("mt-1.5 text-[12px] font-semibold tabular-nums", changeTone(chip.delta, chip.deltaKind ?? "measurement"))}>
          {changeArrow(chip.delta)}{" "}
          {chip.deltaKind === "risk" ? formatPp(chip.delta) : `${Math.abs(chip.delta)} ${chip.unit ?? ""}`.trim()}
        </p>
      ) : null}
    </article>
  );
});

export function ChildModelHud({
  children,
  stageFooter,
  childId,
  compact = false,
  weight,
  height,
  previousWeight,
  previousHeight,
  weightHistory,
  heightHistory,
  probabilityHistory,
  ageMonths,
  sex,
  latestAssessment,
  assessmentLabel = "Latest assessment date",
  status,
  statusLabel = "Status",
  severity,
  probability,
  previousProbability,
  probabilityChange,
  progress,
  riskVelocity,
  scoreLabel = "12-month GA-RGCA prediction",
  scoreTip = "12-month GA-RGCA prediction from the measurements recorded at this visit. Clinical review required.",
  velocityLabel = "Risk Velocity",
  velocityTip = "Visit-to-visit change in model-assessed probability, adjusted for elapsed time. Clinical review required.",
}: {
  children: ReactNode;
  stageFooter?: ReactNode;
  childId?: string | null;
  compact?: boolean;
  weight?: number | null;
  height?: number | null;
  previousWeight?: number | null;
  previousHeight?: number | null;
  weightHistory: number[];
  heightHistory: number[];
  probabilityHistory?: number[];
  ageMonths: number;
  sex: string;
  latestAssessment?: string | null;
  assessmentLabel?: string;
  status: string;
  statusLabel?: string;
  severity?: string | null;
  probability: string;
  previousProbability?: string | null;
  probabilityChange?: number | null;
  progress: string;
  riskVelocity: string;
  scoreLabel?: string;
  scoreTip?: string;
  velocityLabel?: string;
  velocityTip?: string;
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const chipRefs = useRef<Record<string, HTMLElement | null>>({});
  const [paths, setPaths] = useState<Record<string, LinkPath>>({});

  const chips: Chip[] = useMemo(() => {
    const fmtShort = (n: number | null | undefined, unit: string) => (n == null ? "—" : `${n.toFixed(1)} ${unit}`);
    return [
      {
        id: "age",
        label: "Age",
        value: `${ageMonths} mo`,
        side: "left",
      },
      {
        id: "sex",
        label: "Sex",
        value: sex,
        side: "left",
      },
      {
        id: "weight",
        label: "Weight",
        value: fmtShort(weight, "kg"),
        hint: compact ? null : previousWeight != null ? `previous ${previousWeight.toFixed(1)} kg` : null,
        delta: compact ? null : measurementDelta(weight ?? null, previousWeight ?? null),
        deltaKind: "measurement",
        unit: "kg",
        history: compact ? undefined : weightHistory,
        side: "left",
      },
      {
        id: "height",
        label: "Height",
        value: fmtShort(height, "cm"),
        hint: compact ? null : previousHeight != null ? `previous ${previousHeight.toFixed(1)} cm` : null,
        delta: compact ? null : measurementDelta(height ?? null, previousHeight ?? null),
        deltaKind: "measurement",
        unit: "cm",
        history: compact ? undefined : heightHistory,
        side: "left",
      },
      {
        id: "status",
        label: statusLabel,
        value: status,
        secondaryLabel: compact || !severity ? null : "Severity",
        secondaryValue: compact || !severity ? null : severity,
        side: "right",
      },
      {
        id: "probability",
        label: compact ? "Risk" : scoreLabel,
        value: probability,
        hint: compact ? null : previousProbability ? `previous ${previousProbability}` : null,
        delta: compact ? null : probabilityChange,
        deltaKind: "risk",
        unit: "pp",
        history: compact ? undefined : probabilityHistory,
        side: "right",
        valueTestId: "primary-probability",
        labelTip: scoreTip,
      },
    ];
  }, [
    compact,
    ageMonths,
    sex,
    weight,
    previousWeight,
    weightHistory,
    height,
    previousHeight,
    heightHistory,
    status,
    statusLabel,
    severity,
    probability,
    previousProbability,
    probabilityChange,
    probabilityHistory,
    progress,
    riskVelocity,
    scoreLabel,
    scoreTip,
    velocityLabel,
    velocityTip,
    assessmentLabel,
    latestAssessment,
  ]);

  const left = chips.filter((c) => c.side === "left");
  const right = chips.filter((c) => c.side === "right");

  useLayoutEffect(() => {
    const root = rootRef.current;
    const stage = stageRef.current;
    if (!root || !stage) return;

    const sync = () => {
      const rb = root.getBoundingClientRect();
      const sb = stage.getBoundingClientRect();
      if (rb.width < 8 || rb.height < 8 || sb.width < 8) return;
      const fmt = (value: number) => Math.round(value * 100) / 100;
      const toX = (px: number) => ((px - rb.left) / rb.width) * 100;
      const toY = (px: number) => ((px - rb.top) / rb.height) * 100;
      const coreX = fmt(toX(sb.left + sb.width / 2));
      const coreY = fmt(toY(sb.top + sb.height / 2));
      const next: Record<string, LinkPath> = {};
      for (const chip of chips) {
        const el = chipRefs.current[chip.id];
        if (!el) continue;
        const box = el.getBoundingClientRect();
        if (box.width < 4) continue;
        const y = fmt(toY(box.top + box.height / 2));
        const x = fmt(chip.side === "left" ? toX(box.right) - 0.4 : toX(box.left) + 0.4);
        const pull = chip.side === "left" ? 1 : -1;
        const midX = fmt(x + pull * Math.min(10, Math.abs(coreX - x) * 0.45));
        next[chip.id] = {
          d: `M ${x} ${y} C ${midX} ${y}, ${fmt(coreX - pull * 5)} ${coreY}, ${coreX} ${coreY}`,
          x,
          y,
        };
      }
      setPaths((prev) => {
        const ids = Object.keys(next);
        if (
          ids.length === Object.keys(prev).length &&
          ids.every((id) => prev[id]?.d === next[id].d && prev[id]?.x === next[id].x && prev[id]?.y === next[id].y)
        ) {
          return prev;
        }
        return next;
      });
    };

    const frame = requestAnimationFrame(sync);
    const observer = new ResizeObserver(() => requestAnimationFrame(sync));
    observer.observe(root);
    observer.observe(stage);
    chips.forEach((chip) => {
      const el = chipRefs.current[chip.id];
      if (el) observer.observe(el);
    });
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [chips]);

  return (
    <div ref={rootRef} className="relative">
      <svg
        className="pointer-events-none absolute inset-0 z-[1] hidden h-full w-full lg:block"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden
      >
        {chips.map((chip) => {
          const path = paths[chip.id];
          if (!path) return null;
          return (
            <g key={chip.id}>
              <path d={path.d} className="hud-connector" />
              <circle cx={path.x} cy={path.y} r="0.55" className="hud-node" />
            </g>
          );
        })}
      </svg>

      <div className="relative z-[2] grid items-stretch gap-5 md:grid-cols-[minmax(180px,24%)_minmax(0,1fr)_minmax(180px,24%)] md:gap-7 lg:gap-8">
        <div className="order-2 flex flex-col justify-center gap-3 md:order-1">
          {left.map((chip, index) => (
            <ChipCard
              key={chip.id}
              ref={(el) => {
                chipRefs.current[chip.id] = el;
              }}
              chip={chip}
              delay={index * 60}
              compact={compact}
            />
          ))}
        </div>

        <div className="child-stage-well order-1 relative flex min-h-[320px] flex-col md:order-2 md:min-h-[480px]">
          <div className="clinical-halo" aria-hidden />
          <div ref={stageRef} className="relative z-[1] flex min-h-[320px] flex-1 flex-col md:min-h-[480px]" aria-label={childId ? `Progress figure for ${childId}` : undefined}>
            {childId ? <ChildIdHeadTag childId={childId} /> : null}
            <div className="relative min-h-0 flex-1">{children}</div>
          </div>
          {stageFooter ? <div className="relative z-[2] mt-3 flex shrink-0 justify-center">{stageFooter}</div> : null}
        </div>

        <div className="order-3 flex flex-col justify-center gap-3">
          {right.map((chip, index) => (
            <ChipCard
              key={chip.id}
              ref={(el) => {
                chipRefs.current[chip.id] = el;
              }}
              chip={chip}
              delay={index * 60}
              compact={compact}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
