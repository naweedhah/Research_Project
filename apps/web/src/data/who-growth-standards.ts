/**
 * WHO Child Growth Standards: z-scores and the current (measured)
 * UNDERNUTRITION assessment of a child under five.
 *
 * This describes today's anthropometry only. It is independent of the GA-RGCA
 * 12-month risk prediction and must not be mixed with it. The research scope
 * is undernutrition, so this module never classifies overweight, obesity or
 * BMI-for-age; positive z-scores are reported but do not produce a condition.
 *
 * Threshold convention (frozen): strict "< -2" on each indicator.
 *   Underweight  weight-for-age z (WAZ) < -2
 *   Stunting     length/height-for-age z (HAZ) < -2
 *   Wasting      weight-for-length/height z (WHZ) < -2
 *     MAM        -3 <= WHZ < -2
 *     SAM        WHZ < -3
 *
 * When wasting is present the label also names the MAM or SAM category,
 * e.g. "Wasting (MAM)". MUAC and bilateral pitting oedema are not captured
 * by the visit form, so wasting here is WHZ-only.
 */

import {
  HFA_BOYS,
  HFA_GIRLS,
  LFA_BOYS,
  LFA_GIRLS,
  WFA_BOYS,
  WFA_GIRLS,
  WFH_BOYS,
  WFH_GIRLS,
  WFL_BOYS,
  WFL_GIRLS,
  type LmsRow,
} from "./who-lms-tables";

export type WhoSex = "male" | "female";

export type WhoZScores = {
  waz: number | null;
  haz: number | null;
  whz: number | null;
};

/**
 * Current anthropometric undernutrition conditions. Deliberately a separate
 * type from the GA-RGCA predicted type (Normal / Underweight / Stunting / MAM /
 * SAM); the two must not be interchanged.
 */
export type CurrentUndernutritionCondition = "Underweight" | "Stunting" | "Wasting";
export type WastingCategory = "MAM" | "SAM";

export const UNDERNUTRITION_Z_CUTOFF = -2;
export const SAM_Z_CUTOFF = -3;
export const NO_UNDERNUTRITION_LABEL = "No undernutrition detected";

export type UndernutritionAssessment = {
  /** Doctor-facing label: "No undernutrition detected" or e.g. "Underweight + Wasting (MAM)". */
  label: string;
  current_undernutrition_conditions: CurrentUndernutritionCondition[];
  /** Present only when wasting is classified. WHO WHZ: MAM -3..-2, SAM < -3. */
  wastingCategory: WastingCategory | null;
};

export type WhoUndernutritionStatus = UndernutritionAssessment & {
  zScores: WhoZScores;
  /** Which weight-for-size table was used. */
  wastingReference: "weight-for-length" | "weight-for-height" | null;
};

const MIN_AGE_MONTHS = 0;
const MAX_AGE_MONTHS = 60;

function normaliseSex(sex: string | null | undefined): WhoSex | null {
  const v = (sex ?? "").trim().toLowerCase();
  if (v === "male" || v === "m" || v === "boy") return "male";
  if (v === "female" || v === "f" || v === "girl") return "female";
  return null;
}

/** Linear interpolation of L, M, S between the two surrounding table rows. */
function interpolateLms(table: readonly LmsRow[], x: number): { L: number; M: number; S: number } | null {
  if (!table.length) return null;
  const first = table[0];
  const last = table[table.length - 1];
  if (x < first[0] || x > last[0]) return null;
  let lo = 0;
  let hi = table.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (table[mid][0] <= x) lo = mid;
    else hi = mid;
  }
  const a = table[lo];
  const b = table[hi];
  if (a[0] === x || a === b) return { L: a[1], M: a[2], S: a[3] };
  const t = (x - a[0]) / (b[0] - a[0]);
  return {
    L: a[1] + (b[1] - a[1]) * t,
    M: a[2] + (b[2] - a[2]) * t,
    S: a[3] + (b[3] - a[3]) * t,
  };
}

function lmsValueAtZ(lms: { L: number; M: number; S: number }, z: number): number {
  const { L, M, S } = lms;
  if (Math.abs(L) < 1e-9) return M * Math.exp(S * z);
  return M * Math.pow(1 + L * S * z, 1 / L);
}

/**
 * Standard LMS z-score. When `restrictTails` is set (WHO rule for weight-based
 * indicators), values beyond +/-3 SD are rescaled against the distance between
 * the 2 SD and 3 SD curves so extreme weights do not produce runaway z-scores.
 */
function lmsZ(lms: { L: number; M: number; S: number }, y: number, restrictTails: boolean): number {
  const { L, M, S } = lms;
  let z: number;
  if (Math.abs(L) < 1e-9) z = Math.log(y / M) / S;
  else z = (Math.pow(y / M, L) - 1) / (L * S);
  if (!restrictTails) return z;
  if (z > 3) {
    const sd3 = lmsValueAtZ(lms, 3);
    const sd2 = lmsValueAtZ(lms, 2);
    return 3 + (y - sd3) / (sd3 - sd2);
  }
  if (z < -3) {
    const sd3 = lmsValueAtZ(lms, -3);
    const sd2 = lmsValueAtZ(lms, -2);
    return -3 + (y - sd3) / (sd2 - sd3);
  }
  return z;
}

function finite(v: unknown): number | null {
  const n = typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
}

export function whoZScores(input: {
  ageMonths: number | string | null | undefined;
  sex: string | null | undefined;
  weightKg: number | string | null | undefined;
  heightCm: number | string | null | undefined;
}): WhoZScores & { wastingReference: WhoUndernutritionStatus["wastingReference"] } {
  const empty = { waz: null, haz: null, whz: null, wastingReference: null as WhoUndernutritionStatus["wastingReference"] };
  const sex = normaliseSex(input.sex);
  const age = finite(input.ageMonths);
  const weight = finite(input.weightKg);
  const height = finite(input.heightCm);
  if (!sex || age === null || age < MIN_AGE_MONTHS || age > MAX_AGE_MONTHS) return empty;

  const boys = sex === "male";
  const useLength = age < 24;

  let waz: number | null = null;
  if (weight !== null && weight > 0) {
    const lms = interpolateLms(boys ? WFA_BOYS : WFA_GIRLS, age);
    if (lms) waz = lmsZ(lms, weight, true);
  }

  let haz: number | null = null;
  if (height !== null && height > 0) {
    const table = useLength ? (boys ? LFA_BOYS : LFA_GIRLS) : boys ? HFA_BOYS : HFA_GIRLS;
    const lms = interpolateLms(table, age);
    if (lms) haz = lmsZ(lms, height, false);
  }

  let whz: number | null = null;
  let wastingReference: WhoUndernutritionStatus["wastingReference"] = null;
  if (weight !== null && weight > 0 && height !== null && height > 0) {
    const table = useLength ? (boys ? WFL_BOYS : WFL_GIRLS) : boys ? WFH_BOYS : WFH_GIRLS;
    const lms = interpolateLms(table, height);
    if (lms) {
      whz = lmsZ(lms, weight, true);
      wastingReference = useLength ? "weight-for-length" : "weight-for-height";
    }
  }

  return { waz, haz, whz, wastingReference };
}

/**
 * Single source of truth for the current undernutrition rule set, applied to
 * already-computed z-scores. Only low values classify; positive z-scores never
 * produce a condition. Each indicator is evaluated independently so overlaps
 * are kept, in the fixed order Underweight, Stunting, Wasting.
 */
export function classifyUndernutrition(z: WhoZScores): UndernutritionAssessment {
  const conditions: CurrentUndernutritionCondition[] = [];
  if (z.waz !== null && z.waz < UNDERNUTRITION_Z_CUTOFF) conditions.push("Underweight");
  if (z.haz !== null && z.haz < UNDERNUTRITION_Z_CUTOFF) conditions.push("Stunting");
  let wastingCategory: WastingCategory | null = null;
  if (z.whz !== null && z.whz < UNDERNUTRITION_Z_CUTOFF) {
    conditions.push("Wasting");
    wastingCategory = z.whz < SAM_Z_CUTOFF ? "SAM" : "MAM";
  }
  const labelParts = conditions.map((c) => (c === "Wasting" && wastingCategory ? `Wasting (${wastingCategory})` : c));
  return {
    label: labelParts.length ? labelParts.join(" + ") : NO_UNDERNUTRITION_LABEL,
    current_undernutrition_conditions: conditions,
    wastingCategory,
  };
}

/**
 * Current WHO undernutrition assessment from today's measurements.
 * Returns null when the inputs are insufficient (missing sex, age outside
 * 0-60 months, or no measurements).
 */
export function assessWhoUndernutrition(input: {
  ageMonths: number | string | null | undefined;
  sex: string | null | undefined;
  weightKg: number | string | null | undefined;
  heightCm: number | string | null | undefined;
}): WhoUndernutritionStatus | null {
  const { waz, haz, whz, wastingReference } = whoZScores(input);
  if (waz === null && haz === null && whz === null) return null;
  const zScores = { waz, haz, whz };
  return { ...classifyUndernutrition(zScores), zScores, wastingReference };
}

export function formatZ(z: number | null): string {
  if (z === null || !Number.isFinite(z)) return "—";
  const rounded = Math.round(z * 100) / 100;
  return `${rounded > 0 ? "+" : ""}${rounded.toFixed(2)}`;
}
