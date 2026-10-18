"use client";

import { AlertTriangle, CheckCircle2, Ruler, Stethoscope, TrendingUp, Utensils } from "lucide-react";
import { displayedMalnutritionType, formatHighestConditionRisk, normalCategoryProbability } from "@/data/child-profile";
import { assessWhoUndernutrition, formatZ } from "@/data/who-growth-standards";
import { displayPredictedSeverity, formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";

/**
 * The two assessment cards shown after a visit is recorded and on the child
 * profile overview: today's measured condition (left) and the GA-RGCA
 * prediction (right). Presentation only; no prediction values are derived here
 * beyond the display-only confidence percentage.
 */

const TYPE_TONE: Record<string, { badge: string; bar: string }> = {
  normal: { badge: "border-emerald-200 bg-emerald-50 text-emerald-800", bar: "bg-emerald-500" },
  underweight: { badge: "border-amber-200 bg-amber-50 text-amber-800", bar: "bg-amber-500" },
  stunting: { badge: "border-amber-200 bg-amber-50 text-amber-800", bar: "bg-amber-500" },
  mam: { badge: "border-orange-200 bg-orange-50 text-orange-800", bar: "bg-orange-500" },
  sam: { badge: "border-red-200 bg-red-50 text-red-800", bar: "bg-red-500" },
};

export function typeTone(value?: string | null) {
  return TYPE_TONE[(value ?? "").trim().toLowerCase()] ?? { badge: "border-slate-200 bg-slate-50 text-slate-700", bar: "bg-slate-400" };
}

function RiskBar({ label, value, flagged }: { label: string; value?: number; flagged: boolean }) {
  const pct = Math.max(0, Math.min(100, (value ?? 0) * 100));
  const tone = typeTone(label);
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className={flagged ? "font-semibold text-[#0f2744]" : "text-[#475569]"}>{label}</span>
        <span className={`tabular-nums ${flagged ? "font-semibold text-[#0f2744]" : "text-[#64748b]"}`}>{formatPercent(value)}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-[#e8eef5]">
        <div className={`h-full rounded-full ${flagged ? tone.bar : "bg-[#b7cbe0]"}`} style={{ width: `${Math.max(pct, value ? 2 : 0)}%` }} />
      </div>
    </div>
  );
}

function ResultStat({ label, value, unit, note }: { label: string; value: string; unit?: string; note?: string | null }) {
  return (
    <div className="rounded-xl bg-white/80 px-3 py-2.5 ring-1 ring-[#e4ecf4]">
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tabular-nums text-[#0f2744]">
        {value}
        {unit ? <span className="ml-1 text-xs font-medium text-[#64748b]">{unit}</span> : null}
      </p>
      {note ? <p className="mt-0.5 text-[11px] font-medium tabular-nums text-[#64748b]">{note}</p> : null}
    </div>
  );
}

function displayValue(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

function deltaNote(current: number | string | null | undefined, previous: number | string | null | undefined, unit: string): string | null {
  const c = typeof current === "number" ? current : Number(current);
  const p = typeof previous === "number" ? previous : Number(previous);
  if (!Number.isFinite(c) || !Number.isFinite(p) || current === "" || previous === "" || current == null || previous == null) return null;
  const d = Math.round((c - p) * 100) / 100;
  if (d === 0) return `No change (${p} ${unit})`;
  return `${d > 0 ? "+" : ""}${d} ${unit} since last visit`;
}

export type FeedingSummary = {
  breastfeeding_status?: string | null;
  /** "yes" | "no" | "" or boolean */
  complementary_feeding?: string | boolean | null;
  meal_frequency?: string | number | null;
  micronutrient_supplementation?: string | boolean | null;
};

function yesNo(v: string | boolean | null | undefined): string {
  if (v === true || v === "yes") return "Yes";
  if (v === false || v === "no") return "No";
  return "—";
}

function mealsLabel(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  if (n === 0) return "0";
  if (n <= 2) return "1–2";
  if (n <= 4) return "3–4";
  return "5+";
}

export function CurrentConditionCard({
  eyebrow = "Today",
  title = "Current condition",
  weightKg,
  heightCm,
  ageMonths,
  sex,
  previous,
  feeding,
  className = "",
  id,
}: {
  eyebrow?: string;
  title?: string;
  weightKg: number | string | null | undefined;
  heightCm: number | string | null | undefined;
  ageMonths: number | string | null | undefined;
  sex: string | null | undefined;
  previous?: { weightKg?: number | string | null; heightCm?: number | string | null } | null;
  feeding?: FeedingSummary | null;
  className?: string;
  id?: string;
}) {
  const whoStatus = assessWhoUndernutrition({ ageMonths, sex, weightKg, heightCm });
  const whoConditions = whoStatus?.current_undernutrition_conditions ?? [];
  const whoTone = whoStatus
    ? whoStatus.wastingCategory === "SAM"
      ? typeTone("SAM")
      : whoStatus.wastingCategory === "MAM"
        ? typeTone("MAM")
        : whoConditions.length
          ? typeTone("Underweight")
          : typeTone("Normal")
    : typeTone(null);
  const ageDisplay = (() => {
    const n = Number(ageMonths);
    if (ageMonths === "" || ageMonths == null || !Number.isFinite(n)) return "—";
    return String(Math.round(n * 10) / 10);
  })();
  const feedingItems = [
    { label: "Breastfeeding", value: feeding?.breastfeeding_status ? formatStatus(feeding.breastfeeding_status) : "—" },
    { label: "Complementary foods", value: yesNo(feeding?.complementary_feeding) },
    { label: "Meals / day", value: mealsLabel(feeding?.meal_frequency) },
    { label: "Micronutrients", value: yesNo(feeding?.micronutrient_supplementation) },
  ];

  return (
    <section id={id} className={`rounded-2xl border border-[#d7e4f2] bg-gradient-to-br from-[#f4f8fc] to-white p-4 ${className}`}>
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-[#EAF2FA] p-2 text-[#0E3A67]">
          <Stethoscope className="h-4 w-4" />
        </span>
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">{eyebrow}</p>
          <p className="text-sm font-semibold text-[#0f2744]">{title}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <ResultStat label="Weight" value={displayValue(weightKg)} unit="kg" note={previous ? deltaNote(weightKg, previous.weightKg, "kg") : null} />
        <ResultStat label="Height" value={displayValue(heightCm)} unit="cm" note={previous ? deltaNote(heightCm, previous.heightCm, "cm") : null} />
        <ResultStat label="Age" value={ageDisplay} unit="mo" />
      </div>

      <div className="mt-3 rounded-xl bg-white/80 px-3 py-2.5 ring-1 ring-[#e4ecf4]">
        <div className="flex items-center gap-2 text-sm text-[#475569]">
          <Ruler className="h-4 w-4 text-[#0E3A67]" />
          WHO Undernutrition Assessment
        </div>
        <div className="mt-1.5">
          <span className={`inline-block rounded-full border px-3 py-1 text-base font-bold ${whoTone.badge}`}>
            {whoStatus ? whoStatus.label : "Not assessed"}
          </span>
        </div>
        {whoStatus ? (
          <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
            {[
              { k: "Weight-for-age", z: whoStatus.zScores.waz, flag: whoConditions.includes("Underweight") },
              { k: "Height-for-age", z: whoStatus.zScores.haz, flag: whoConditions.includes("Stunting") },
              { k: "Weight-for-height", z: whoStatus.zScores.whz, flag: whoConditions.includes("Wasting") },
            ].map((item) => (
              <div key={item.k} className={`rounded-lg px-2 py-1.5 ${item.flag ? "bg-amber-50" : "bg-[#f4f8fc]"}`}>
                <dt className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#94a3b8]">{item.k}</dt>
                <dd className={`text-sm font-semibold tabular-nums ${item.flag ? "text-amber-800" : "text-[#0f2744]"}`}>
                  {formatZ(item.z)} <span className="text-[10px] font-medium text-[#94a3b8]">z</span>
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-1 text-xs text-[#64748b]">WHO standards cover 0–60 months with sex, weight and height recorded.</p>
        )}
      </div>

      <div className="mt-3 rounded-xl bg-white/80 px-3 py-2.5 ring-1 ring-[#e4ecf4]">
        <div className="flex items-center gap-2 text-sm text-[#475569]">
          <Utensils className="h-4 w-4 text-[#0E3A67]" />
          Feeding today
        </div>
        <dl className="mt-2 grid grid-cols-2 gap-2">
          {feedingItems.map((item) => (
            <div key={item.label} className="rounded-lg bg-[#f4f8fc] px-2.5 py-1.5">
              <dt className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#94a3b8]">{item.label}</dt>
              <dd className="text-sm font-semibold text-[#0f2744]">{item.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

export type PredictionCardData = {
  severity?: string | null;
  risk?: number | null;
  predicted_malnutrition_type?: string | null;
  detected_conditions?: string[] | null;
  ga_rgca?: {
    underweight_probability?: number;
    stunting_probability?: number;
    mam_probability?: number;
    sam_probability?: number;
    predicted_malnutrition_type?: string | null;
    detected_conditions?: string[];
    severity?: string;
    uncertainty_flag?: boolean;
    binary_variance?: number;
    triage?: string;
  } | null;
};

export function PredictionCard({ prediction, className = "", id }: { prediction: PredictionCardData; className?: string; id?: string }) {
  const ga = prediction.ga_rgca;
  const predictedType = formatNutritionalStatus(displayedMalnutritionType(prediction), ga?.severity ?? prediction.severity ?? undefined);
  const predictedTone = typeTone(predictedType);
  const severityLabel = displayPredictedSeverity(displayedMalnutritionType(prediction), ga?.severity ?? prediction.severity);
  const detected = (ga?.detected_conditions ?? prediction.detected_conditions ?? []).map((c) => c.toLowerCase());
  const flagged = (name: string) => detected.includes(name.toLowerCase());
  const severityTone = (() => {
    const s = (ga?.severity ?? "").toLowerCase();
    if (s === "severe") return typeTone("SAM");
    if (s === "moderate") return typeTone("Underweight");
    if (s === "normal") return typeTone("Normal");
    return typeTone(null);
  })();
  // Display-only ensemble agreement: 1 - 2*std of the three ensemble members' binary
  // probabilities (std 0 = 100%, the theoretical maximum std of 0.5 = 0%). Derived from the
  // existing binary_variance; the uncertainty flag itself is unchanged and still shown.
  const confidenceScore =
    typeof ga?.binary_variance === "number" && ga.binary_variance >= 0
      ? Math.max(0, Math.min(1, 1 - 2 * Math.sqrt(ga.binary_variance)))
      : null;

  return (
    <section id={id} className={`rounded-2xl border border-[#0E3A67]/15 bg-gradient-to-br from-[#0E3A67] to-[#1b4f86] p-4 text-white ${className}`}>
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-white/15 p-2">
          <TrendingUp className="h-4 w-4" />
        </span>
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-white/70">Prediction</p>
          <p className="text-sm font-semibold">Predicted nutritional risk</p>
        </div>
      </div>

      <div className="mt-4 rounded-xl bg-white p-4 text-[#0f2744]">
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">Predicted malnutrition type</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <span className={`rounded-full border px-3 py-1 text-base font-bold ${predictedTone.badge}`}>{predictedType}</span>
          {severityLabel ? (
            <span className={`rounded-full border px-2.5 py-1 text-sm font-semibold ${severityTone.badge}`}>Severity: {severityLabel}</span>
          ) : null}
        </div>

        {ga ? (
          <div className="mt-4 space-y-3">
            <RiskBar label="Normal" value={normalCategoryProbability(ga) ?? undefined} flagged={predictedType === "Normal"} />
            <RiskBar label="Underweight" value={ga.underweight_probability} flagged={flagged("Underweight")} />
            <RiskBar label="Stunting" value={ga.stunting_probability} flagged={flagged("Stunting")} />
            <RiskBar label="MAM" value={ga.mam_probability} flagged={flagged("MAM")} />
            <RiskBar label="SAM" value={ga.sam_probability} flagged={flagged("SAM")} />
            <p className="border-t border-[#e8eef5] pt-2.5 text-xs text-[#64748b]">
              Highest predicted condition risk: <span className="font-semibold text-[#0f2744]">{formatHighestConditionRisk(prediction)}</span>.
              Normal is 1 minus that value. Alerts and trends track the highest condition risk.
            </p>
          </div>
        ) : (
          <p className="mt-3 text-sm text-[#475569]">
            12-month GA-RGCA prediction <strong className="text-[#0f2744]">{formatPercent(prediction.risk ?? undefined)}</strong>
          </p>
        )}
      </div>

      {ga ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <div className="rounded-xl bg-white/10 px-3 py-2.5 ring-1 ring-white/15">
            <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-white/70">Recommendation</p>
            <p className="mt-0.5 text-sm font-semibold">{ga.triage ?? "Clinical review"}</p>
          </div>
          <div className="rounded-xl bg-white/10 px-3 py-2.5 ring-1 ring-white/15">
            <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-white/70">Model confidence</p>
            <p className="mt-0.5 flex items-center gap-1.5 text-sm font-semibold">
              {ga.uncertainty_flag ? <AlertTriangle className="h-4 w-4 text-amber-300" /> : <CheckCircle2 className="h-4 w-4 text-emerald-300" />}
              {confidenceScore !== null ? (
                <span className="text-lg tabular-nums">{Math.round(confidenceScore * 100)}%</span>
              ) : ga.uncertainty_flag ? (
                "Elevated uncertainty"
              ) : (
                "Low uncertainty"
              )}
            </p>
          </div>
        </div>
      ) : null}
    </section>
  );
}
