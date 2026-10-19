import { ageMonthsAtVisit, displayedMalnutritionType, type ChildProfile, type ProfilePrediction, type ProfileVisit } from "@/data/child-profile";
import { assessWhoUndernutrition, NO_UNDERNUTRITION_LABEL } from "@/data/who-growth-standards";
import { formatNutritionalStatus } from "@/utils/utils";

/** Doctor-facing current WHO label for one recorded visit. Uses the frozen WHO rules only. */
export function whoLabelForVisit(profile: Pick<ChildProfile, "date_of_birth" | "age_months" | "sex">, visit?: ProfileVisit | null): string {
  const weight = visit?.measurements?.weight_kg;
  const height = visit?.measurements?.height_cm;
  if (!visit || weight == null || height == null) return "Not assessed";
  const age = ageMonthsAtVisit(profile.date_of_birth, visit.visit_date, profile.age_months);
  const who = assessWhoUndernutrition({ ageMonths: age, sex: profile.sex, weightKg: weight, heightCm: height });
  if (!who) return "Not assessed";
  return who.label === NO_UNDERNUTRITION_LABEL ? "Normal" : who.label;
}

export function predictionLabel(prediction?: ProfilePrediction | null): string {
  const type = displayedMalnutritionType(prediction);
  return type ? formatNutritionalStatus(type, prediction?.severity) : "No prediction stored";
}

export type MeasurementChange = { value: number; text: string; direction: "up" | "down" | "same" };

export function measurementChange(current?: number | null, previous?: number | null, unit = "kg"): MeasurementChange | null {
  if (current == null || previous == null) return null;
  const diff = Math.round((current - previous) * 100) / 100;
  const direction = diff > 0 ? "up" : diff < 0 ? "down" : "same";
  const sign = diff > 0 ? "+" : "";
  return { value: diff, text: `${sign}${diff} ${unit}`, direction };
}

/** Stored uncertainty flag, worded for a clinician. No new threshold is applied. */
export function uncertaintyState(prediction?: ProfilePrediction | null): { label: string; detail: string; flagged: boolean | null } {
  const flag = prediction?.ga_rgca?.uncertainty_flag;
  if (flag == null) return { label: "Not available", detail: "No uncertainty signal is stored for this prediction.", flagged: null };
  if (flag) {
    return {
      label: "Additional clinician review recommended",
      detail: "The model marked this prediction as uncertain. Confirm the measurements and context before acting on it.",
      flagged: true,
    };
  }
  return { label: "Low review signal", detail: "The model did not flag this prediction as uncertain. Clinician confirmation is still required.", flagged: false };
}

/** Stored applicability flag, worded as similarity to the training population. */
export function applicabilityState(prediction?: ProfilePrediction | null): { label: string; detail: string; outside: boolean | null } {
  const ood = prediction?.ga_rgca?.out_of_distribution_flag;
  const distance = prediction?.ga_rgca?.latent_distance;
  const distanceText = distance != null ? ` Latent distance ${Number(distance).toFixed(2)}.` : "";
  if (ood == null) return { label: "Not available", detail: "No applicability signal is stored.", outside: null };
  if (ood) {
    return {
      label: "Outside internal reference range",
      detail: `This child's profile sits outside the internal reference used during training.${distanceText} This internal signal is not externally validated.`,
      outside: true,
    };
  }
  return {
    label: "Within reference range",
    detail: `This child's profile is similar to the training population.${distanceText} This internal signal is not externally validated.`,
    outside: false,
  };
}

export function dataQualityState(profile: Pick<ChildProfile, "data_quality_label" | "data_quality">): { label: string; tone: "ok" | "warn" | "muted"; detail: string } {
  const quality = profile.data_quality as { blocking_errors?: { message?: string }[]; warnings?: { message?: string }[]; missing?: string[] } | null | undefined;
  const warnings = quality?.warnings?.map((w) => w.message).filter((m): m is string => Boolean(m)) ?? [];
  const blocking = quality?.blocking_errors?.map((w) => w.message).filter((m): m is string => Boolean(m)) ?? [];
  const optionalMissing = warnings.filter((m) => /optional field/i.test(m)).length;
  const otherWarnings = warnings.filter((m) => !/optional field/i.test(m));
  const optionalNote = optionalMissing > 0 ? `${optionalMissing} optional field${optionalMissing === 1 ? "" : "s"} not recorded; this does not block the assessment.` : "";
  if (profile.data_quality_label === "review_required") {
    return {
      label: "Measurement requires review",
      tone: "warn",
      detail: [...blocking, ...otherWarnings].join(" ") || "Recorded information did not pass all validation checks.",
    };
  }
  if (profile.data_quality_label === "complete") {
    return {
      label: "Complete",
      tone: "ok",
      detail: ["Required measurements and context were recorded.", ...otherWarnings, optionalNote].filter(Boolean).join(" "),
    };
  }
  return { label: "Not evaluated", tone: "muted", detail: "No data-quality result is stored for the latest visit." };
}
