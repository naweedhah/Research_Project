/**
 * Facility clinic board: today's WHO measurements versus the 12-month
 * prediction, plus weight loss between the last two visits.
 *
 * This is not the child register, the dashboard review queue, or a
 * per-child progress chart.
 */

import { displayedMalnutritionType } from "@/data/child-profile";
import {
  NO_UNDERNUTRITION_LABEL,
  assessWhoUndernutrition,
  type WhoUndernutritionStatus,
} from "@/data/who-growth-standards";
import { formatNutritionalStatus } from "@/utils/utils";

/** Ignore sub-100 g changes; they are usually scale noise, not loss. */
export const WEIGHT_LOSS_KG = 0.1;

const PREDICTED_RISK_TYPES = new Set(["Underweight", "Stunting", "MAM", "SAM"]);
const PREDICTED_RANK = ["SAM", "MAM", "Stunting", "Underweight"];

export type ClinicChildInput = {
  id: string;
  pseudonymous_id: string;
  full_name?: string | null;
  age_months: number;
  sex: string;
  last_visit?: string;
  has_assessment?: boolean;
  current_status?: string | null;
  predicted_malnutrition_type?: string | null;
  severity?: string | null;
  predicted_type_probability?: number | null;
  measurements?: {
    weight_kg?: number | null;
    height_cm?: number | null;
    previous_weight_kg?: number | null;
  } | null;
};

export type ClinicBoardRow = {
  id: string;
  pseudonymous_id: string;
  full_name?: string | null;
  age_months: number;
  sex: string;
  last_visit?: string;
  whoLabel: string;
  predictedLabel: string;
  reason: string;
  weightDeltaKg?: number;
  /** Pass-through for display. Not used to decide which tray a child belongs to. */
  predictedTypeProbability: number | null;
  weightKg: number | null;
  previousWeightKg: number | null;
};

export type ClinicBoardGroups = {
  wellTodayPredictedRisk: ClinicBoardRow[];
  undernourishedTodayDifferentPrediction: ClinicBoardRow[];
  weightLowerThanLastVisit: ClinicBoardRow[];
};

export function whoComparableTokens(who: WhoUndernutritionStatus | null): string[] {
  if (!who) return [];
  const tokens: string[] = [];
  for (const condition of who.current_undernutrition_conditions) {
    if (condition === "Wasting") {
      if (who.wastingCategory) tokens.push(who.wastingCategory);
      continue;
    }
    tokens.push(condition);
  }
  return tokens;
}

export function predictedTypeLabel(child: ClinicChildInput): string | null {
  if (child.has_assessment === false) return null;
  const type = displayedMalnutritionType(child);
  if (!type) return null;
  const label = formatNutritionalStatus(type, child.severity);
  return label === "—" ? null : label;
}

export function currentWhoAssessment(child: ClinicChildInput): WhoUndernutritionStatus | null {
  return assessWhoUndernutrition({
    ageMonths: child.age_months,
    sex: child.sex,
    weightKg: child.measurements?.weight_kg,
    heightCm: child.measurements?.height_cm,
  });
}

function predictedIsRisk(label: string | null): boolean {
  return Boolean(label && PREDICTED_RISK_TYPES.has(label));
}

function toRow(
  child: ClinicChildInput,
  who: WhoUndernutritionStatus | null,
  predicted: string | null,
  reason: string,
  weightDeltaKg?: number,
): ClinicBoardRow {
  return {
    id: child.id,
    pseudonymous_id: child.pseudonymous_id,
    full_name: child.full_name,
    age_months: child.age_months,
    sex: child.sex,
    last_visit: child.last_visit,
    whoLabel: who?.label ?? "Measurements incomplete",
    predictedLabel: predicted ?? "No prediction yet",
    reason,
    weightDeltaKg,
    predictedTypeProbability:
      typeof child.predicted_type_probability === "number" && Number.isFinite(child.predicted_type_probability)
        ? child.predicted_type_probability
        : null,
    weightKg: typeof child.measurements?.weight_kg === "number" ? child.measurements.weight_kg : null,
    previousWeightKg: typeof child.measurements?.previous_weight_kg === "number" ? child.measurements.previous_weight_kg : null,
  };
}

function rankPredicted(label: string): number {
  const index = PREDICTED_RANK.indexOf(label);
  return index === -1 ? PREDICTED_RANK.length : index;
}

function sortPredictedRisk(a: ClinicBoardRow, b: ClinicBoardRow): number {
  const rank = rankPredicted(a.predictedLabel) - rankPredicted(b.predictedLabel);
  if (rank !== 0) return rank;
  return a.pseudonymous_id.localeCompare(b.pseudonymous_id);
}

export function classifyClinicBoard(children: ClinicChildInput[]): ClinicBoardGroups {
  const wellTodayPredictedRisk: ClinicBoardRow[] = [];
  const undernourishedTodayDifferentPrediction: ClinicBoardRow[] = [];
  const weightLowerThanLastVisit: ClinicBoardRow[] = [];

  for (const child of children) {
    const who = currentWhoAssessment(child);
    const predicted = predictedTypeLabel(child);
    const whoTokens = whoComparableTokens(who);

    if (who && who.current_undernutrition_conditions.length === 0 && predictedIsRisk(predicted)) {
      wellTodayPredictedRisk.push(
        toRow(
          child,
          who,
          predicted,
          `Last measurements show no undernutrition. The 12-month prediction is ${predicted}.`,
        ),
      );
    }

    if (who && whoTokens.length > 0 && predicted) {
      const agrees = predicted === "Normal" ? false : whoTokens.includes(predicted);
      if (!agrees) {
        undernourishedTodayDifferentPrediction.push(
          toRow(
            child,
            who,
            predicted,
            `Last measurements: ${who.label}. 12-month prediction: ${predicted}.`,
          ),
        );
      }
    }

    const current = child.measurements?.weight_kg;
    const previous = child.measurements?.previous_weight_kg;
    if (
      typeof current === "number" &&
      Number.isFinite(current) &&
      typeof previous === "number" &&
      Number.isFinite(previous) &&
      current <= previous - WEIGHT_LOSS_KG
    ) {
      const delta = Math.round((current - previous) * 10) / 10;
      const signed = delta.toFixed(1);
      weightLowerThanLastVisit.push(
        toRow(
          child,
          who,
          predicted,
          `Weight ${previous.toFixed(1)} kg → ${current.toFixed(1)} kg (${signed} kg).`,
          current - previous,
        ),
      );
    }
  }

  wellTodayPredictedRisk.sort(sortPredictedRisk);
  undernourishedTodayDifferentPrediction.sort((a, b) => {
    const whoRank =
      (a.whoLabel.includes("SAM") ? 0 : a.whoLabel.includes("MAM") ? 1 : 2) -
      (b.whoLabel.includes("SAM") ? 0 : b.whoLabel.includes("MAM") ? 1 : 2);
    if (whoRank !== 0) return whoRank;
    return a.pseudonymous_id.localeCompare(b.pseudonymous_id);
  });
  weightLowerThanLastVisit.sort((a, b) => (a.weightDeltaKg ?? 0) - (b.weightDeltaKg ?? 0));

  return {
    wellTodayPredictedRisk,
    undernourishedTodayDifferentPrediction,
    weightLowerThanLastVisit,
  };
}

export type PictureSlice = {
  key: string;
  label: string;
  count: number;
  color: string;
};

export type ClinicBoardPicture = {
  children: number;
  measured: PictureSlice[];
  predicted: PictureSlice[];
  alignment: PictureSlice[];
};

const MEASURED_SLICES: PictureSlice[] = [
  { key: "none", label: "No undernutrition", count: 0, color: "#0f766e" },
  { key: "underweight", label: "Underweight", count: 0, color: "#d97706" },
  { key: "stunting", label: "Stunting", count: 0, color: "#7c3aed" },
  { key: "mam", label: "Wasting (MAM)", count: 0, color: "#ea580c" },
  { key: "sam", label: "Wasting (SAM)", count: 0, color: "#dc2626" },
  { key: "overlap", label: "Multiple findings", count: 0, color: "#0e7490" },
  { key: "incomplete", label: "Measurements incomplete", count: 0, color: "#94a3b8" },
];

const PREDICTED_SLICES: PictureSlice[] = [
  { key: "Normal", label: "Normal", count: 0, color: "#0f766e" },
  { key: "Underweight", label: "Underweight", count: 0, color: "#d97706" },
  { key: "Stunting", label: "Stunting", count: 0, color: "#7c3aed" },
  { key: "MAM", label: "MAM", count: 0, color: "#ea580c" },
  { key: "SAM", label: "SAM", count: 0, color: "#dc2626" },
  { key: "none", label: "No prediction yet", count: 0, color: "#94a3b8" },
];

const ALIGNMENT_SLICES: PictureSlice[] = [
  { key: "same", label: "Same pattern", count: 0, color: "#0f766e" },
  { key: "well-risk", label: "Well today → predicted risk", count: 0, color: "#d97706" },
  { key: "different", label: "Different pattern", count: 0, color: "#dc2626" },
  { key: "incomplete", label: "Not comparable yet", count: 0, color: "#94a3b8" },
];

function bump(slices: PictureSlice[], key: string) {
  const slice = slices.find((item) => item.key === key);
  if (slice) slice.count += 1;
}

function measuredKey(who: WhoUndernutritionStatus | null): string {
  if (!who) return "incomplete";
  if (who.current_undernutrition_conditions.length === 0) return "none";
  if (who.current_undernutrition_conditions.length > 1) return "overlap";
  const only = who.current_undernutrition_conditions[0];
  if (only === "Wasting") return who.wastingCategory === "SAM" ? "sam" : "mam";
  if (only === "Stunting") return "stunting";
  return "underweight";
}

/** Counts for the clinic picture. Each child is in exactly one slice of each chart. */
export function summarizeClinicBoard(children: ClinicChildInput[]): ClinicBoardPicture {
  const measured = MEASURED_SLICES.map((slice) => ({ ...slice }));
  const predicted = PREDICTED_SLICES.map((slice) => ({ ...slice }));
  const alignment = ALIGNMENT_SLICES.map((slice) => ({ ...slice }));

  for (const child of children) {
    const who = currentWhoAssessment(child);
    const predictedLabel = predictedTypeLabel(child);
    const whoTokens = whoComparableTokens(who);
    bump(measured, measuredKey(who));
    bump(predicted, predictedLabel && PREDICTED_SLICES.some((slice) => slice.key === predictedLabel) ? predictedLabel : "none");

    if (!who || !predictedLabel) {
      bump(alignment, "incomplete");
    } else if (who.current_undernutrition_conditions.length === 0 && predictedIsRisk(predictedLabel)) {
      bump(alignment, "well-risk");
    } else if (whoTokens.length > 0 && (predictedLabel === "Normal" || !whoTokens.includes(predictedLabel))) {
      bump(alignment, "different");
    } else {
      bump(alignment, "same");
    }
  }

  return { children: children.length, measured, predicted, alignment };
}

export type AttentionReason = "future-risk" | "pattern-change" | "weight-decline";

export type AttentionCase = ClinicBoardRow & {
  reasons: AttentionReason[];
};

export type AttentionTab = "all" | AttentionReason;
export type PredictedTypeFilter = "all" | "Underweight" | "Stunting" | "MAM" | "SAM";
export type SexFilter = "all" | "female" | "male";
export type AgeBandFilter = "all" | "0-5" | "6-11" | "12-23" | "24-35" | "36-47" | "48-60";
export type AttentionSort = "priority" | "visit" | "age" | "name";

export type AttentionQuery = {
  tab: AttentionTab;
  search: string;
  predictedType: PredictedTypeFilter;
  sex: SexFilter;
  ageBand: AgeBandFilter;
  sort: AttentionSort;
};

const AGE_BANDS: Record<Exclude<AgeBandFilter, "all">, [number, number]> = {
  "0-5": [0, 5],
  "6-11": [6, 11],
  "12-23": [12, 23],
  "24-35": [24, 35],
  "36-47": [36, 47],
  "48-60": [48, 60],
};

/** Unique children in any attention tray. A child in two trays counts once. */
export function needsAttentionIds(groups: ClinicBoardGroups): string[] {
  return [
    ...new Set([
      ...groups.wellTodayPredictedRisk.map((row) => row.id),
      ...groups.undernourishedTodayDifferentPrediction.map((row) => row.id),
      ...groups.weightLowerThanLastVisit.map((row) => row.id),
    ]),
  ];
}

export function dedupeAttentionCases(groups: ClinicBoardGroups): AttentionCase[] {
  const byId = new Map<string, AttentionCase>();
  const add = (row: ClinicBoardRow, reason: AttentionReason) => {
    const current = byId.get(row.id);
    if (!current) {
      byId.set(row.id, { ...row, reasons: [reason] });
      return;
    }
    if (!current.reasons.includes(reason)) current.reasons.push(reason);
    if (row.weightDeltaKg != null) current.weightDeltaKg = row.weightDeltaKg;
  };
  for (const row of groups.wellTodayPredictedRisk) add(row, "future-risk");
  for (const row of groups.undernourishedTodayDifferentPrediction) add(row, "pattern-change");
  for (const row of groups.weightLowerThanLastVisit) add(row, "weight-decline");
  return [...byId.values()];
}

/**
 * Attention priority is a UI worklist ordering heuristic based on existing alerts.
 * It is not a validated clinical severity score.
 * Lower numbers are shown first.
 */
export function attentionPriorityRank(item: Pick<AttentionCase, "predictedLabel" | "whoLabel" | "reasons">): number {
  const weightAndAnother = item.reasons.includes("weight-decline") && item.reasons.some((reason) => reason !== "weight-decline");
  if (item.predictedLabel === "SAM") return 1;
  if (item.predictedLabel === "MAM") return 2;
  if (item.reasons.includes("pattern-change") && item.whoLabel.includes("SAM")) return 3;
  if (item.reasons.includes("pattern-change") && item.whoLabel.includes("MAM")) return 4;
  if (weightAndAnother) return 5;
  if (item.predictedLabel === "Stunting") return 6;
  if (item.predictedLabel === "Underweight") return 7;
  if (item.reasons.includes("pattern-change")) return 8;
  return 9;
}

export function ageInBand(months: number, band: AgeBandFilter): boolean {
  if (band === "all") return true;
  const range = AGE_BANDS[band];
  return months >= range[0] && months <= range[1];
}

export function filterAttentionCases(cases: AttentionCase[], query: AttentionQuery): AttentionCase[] {
  const needle = query.search.trim().toLowerCase();
  return cases.filter((item) => {
    if (query.tab !== "all" && !item.reasons.includes(query.tab)) return false;
    if (needle) {
      const name = (item.full_name ?? "").toLowerCase();
      const id = item.pseudonymous_id.toLowerCase();
      if (!name.includes(needle) && !id.includes(needle)) return false;
    }
    if (query.predictedType !== "all" && item.predictedLabel !== query.predictedType) return false;
    if (query.sex !== "all" && item.sex.trim().toLowerCase() !== query.sex) return false;
    return ageInBand(item.age_months, query.ageBand);
  });
}

export function sortAttentionCases(cases: AttentionCase[], sort: AttentionSort, tab: AttentionTab): AttentionCase[] {
  const copy = [...cases];
  copy.sort((a, b) => {
    if (sort === "priority" && tab === "weight-decline") {
      return (a.weightDeltaKg ?? 0) - (b.weightDeltaKg ?? 0) || a.pseudonymous_id.localeCompare(b.pseudonymous_id);
    }
    if (sort === "visit") {
      const av = a.last_visit ? Date.parse(a.last_visit) : 0;
      const bv = b.last_visit ? Date.parse(b.last_visit) : 0;
      return bv - av || a.pseudonymous_id.localeCompare(b.pseudonymous_id);
    }
    if (sort === "age") return a.age_months - b.age_months || a.pseudonymous_id.localeCompare(b.pseudonymous_id);
    if (sort === "name") {
      const an = (a.full_name?.trim() || a.pseudonymous_id).toLocaleLowerCase();
      const bn = (b.full_name?.trim() || b.pseudonymous_id).toLocaleLowerCase();
      return an.localeCompare(bn);
    }
    return attentionPriorityRank(a) - attentionPriorityRank(b) || a.pseudonymous_id.localeCompare(b.pseudonymous_id);
  });
  return copy;
}

export function presentAttentionCases(cases: AttentionCase[], query: AttentionQuery): AttentionCase[] {
  return sortAttentionCases(filterAttentionCases(cases, query), query.sort, query.tab);
}

export function clinicBoardEmpty(groups: ClinicBoardGroups): boolean {
  return (
    groups.wellTodayPredictedRisk.length === 0 &&
    groups.undernourishedTodayDifferentPrediction.length === 0 &&
    groups.weightLowerThanLastVisit.length === 0
  );
}

export { NO_UNDERNUTRITION_LABEL };
