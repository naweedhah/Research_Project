import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercent(value?: number | null) {
  if (value === null || value === undefined) return "—";
  if (value === 0) return "0%";
  const percent = value * 100;
  if (percent > 0 && percent < 1) return "<1%";
  return `${Math.round(percent)}%`;
}

const STATUS_LABELS: Record<string, string> = {
  mam: "MAM",
  sam: "SAM",
  wasting: "MAM",
  mild_wasting: "MAM",
  moderate_wasting: "MAM",
  severe_wasting: "SAM",
};

/** Doctor-facing nutritional status. Acute malnutrition is MAM or SAM. */
export function formatNutritionalStatus(status?: string | null, severity?: string | null) {
  if (!status) return "—";
  const key = status.trim().toLowerCase().replaceAll(" ", "_");
  const severityKey = (severity ?? "").trim().toLowerCase();
  if (key === "severe_wasting" || (key === "wasting" && severityKey === "severe")) return "SAM";
  if (key === "wasting" || key === "mild_wasting" || key === "moderate_wasting") return "MAM";
  return formatStatus(status);
}

export function formatStatus(value?: string | null) {
  if (!value) return "Unknown";
  const key = value.trim().toLowerCase().replaceAll(" ", "_");
  if (STATUS_LABELS[key]) return STATUS_LABELS[key];
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const PROTOTYPE_LANGUAGE = /demo|dummy|synthetic|demonstration/i;

/** Replace prototype wording with clinic language. */
export function clinicalPhrase(value: string | null | undefined, fallback: string) {
  if (!value || PROTOTYPE_LANGUAGE.test(value)) return fallback;
  return value;
}

export function ageLabel(months?: number | null) {
  if (months === null || months === undefined) return "—";
  if (months < 12) return `${months} months`;
  const years = Math.floor(months / 12);
  const rem = months % 12;
  return rem ? `${years}y ${rem}m` : `${months} months`;
}

const CLINICAL_DATE_LOCALE = "en-GB";

export function formatClinicalDate(
  value?: string | Date | null,
  options: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" },
) {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(CLINICAL_DATE_LOCALE, options);
}

/** Compare calendar dates (YYYY-MM-DD) without timezone drift. */
export function isBeforeToday(isoDate: string) {
  const today = new Date().toISOString().slice(0, 10);
  return isoDate.slice(0, 10) < today;
}
