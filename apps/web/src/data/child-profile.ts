export const PREDICTED_MALNUTRITION_TYPES = ["Normal", "Underweight", "Stunting", "MAM", "SAM"] as const;
export type PredictedMalnutritionType = (typeof PREDICTED_MALNUTRITION_TYPES)[number];

export const ACUTE_MALNUTRITION_STATUSES = ["Normal", "MAM", "SAM"] as const;
export type AcuteMalnutritionStatus = (typeof ACUTE_MALNUTRITION_STATUSES)[number];

export type ProfileMeasurements = {
  weight_kg?: number | null;
  height_cm?: number | null;
  muac_cm?: number | null;
};

export type ProfilePrediction = {
  status?: string;
  predicted_malnutrition_type?: PredictedMalnutritionType | string | null;
  severity?: string;
  risk?: number;
  confidence?: string;
  mode?: string;
  model?: string | null;
  run_number?: number;
  calibration_version?: string | null;
  feature_schema_version?: string | null;
  calibrated_status_probabilities?: Record<string, number> | null;
  ga_rgca?: {
    architecture?: string;
    underweight_probability?: number;
    stunting_probability?: number;
    mam_probability?: number;
    sam_probability?: number;
    underweight_positive?: boolean;
    stunting_positive?: boolean;
    predicted_malnutrition_type?: PredictedMalnutritionType | string;
    detected_conditions?: string[];
    normal_acute_probability?: number;
    acute_status?: AcuteMalnutritionStatus | string;
    acute_probability?: number;
    severity?: string;
    severity_probabilities?: { normal?: number; moderate?: number; severe?: number };
    binary_variance?: number;
    uncertainty_flag?: boolean;
    uncertainty_label?: string;
    triage?: string;
    modality_reliability?: {
      history?: number;
      socioeconomic?: number;
      feeding?: number;
      supplementation?: number;
    };
    model_version?: string;
    prediction_source?: string;
    clinical_use?: boolean;
    disclaimer?: string;
    data_limitations?: string[];
    binary_thresholds?: { Underweight?: number; Stunting?: number };
    input_snapshot?: { values?: Record<string, unknown>; missing_features?: string[] };
    missing_features?: string[];
    applicability?: { message?: string };
    output_consistency?: string;
  } | null;
};

export type ProfileVisit = {
  id: string;
  visit_number: number;
  visit_date: string;
  status?: string;
  data_quality?: Record<string, unknown> | null;
  measurements?: ProfileMeasurements | null;
  prediction?: ProfilePrediction | null;
  progress?: string | null;
  risk_velocity?: number | null;
  baseline_recovery_rate?: number | null;
  model_compatible?: boolean | null;
  warning?: string | null;
  embedding_space_id?: string | null;
  projection_version?: string | null;
  projection?: { x: number; y: number } | null;
  review_status?: string | null;
};

export type ProfileAlert = {
  id: string;
  type: string;
  severity: string;
  status: string;
  message: string;
  headline?: string;
  created_at?: string;
  trigger_value?: { previous_risk?: number; current_risk?: number; risk_velocity?: number; basis?: string };
};

export type ClinicianReview = {
  status: string;
  assessment?: string;
  assessment_key?: string;
  workflow?: string | null;
  workflow_key?: string | null;
  reviewer_name?: string | null;
  note_excerpt?: string;
  created_at?: string | null;
};

export type ModalityCount = {
  available: number;
  total: number;
  fields: { field: string; available: boolean }[];
};

export type ChildProfile = {
  id: string;
  pseudonymous_id: string;
  full_name?: string | null;
  external_patient_id?: string | null;
  age_months: number;
  sex: string;
  date_of_birth?: string;
  facility?: { name: string; code: string; district?: string } | null;
  responsible_team?: string | null;
  district?: string | null;
  moh_area?: string | null;
  phm_area?: string | null;
  assigned_doctor?: { id: string; full_name: string } | null;
  caregiver?: {
    relationship?: string | null;
    display_name?: string | null;
    phone?: string | null;
    reminder_consent?: boolean;
  } | null;
  has_baseline?: boolean;
  visit_count?: number;
  assessment_count?: number;
  current?: ProfileVisit | null;
  previous?: ProfileVisit | null;
  risk_change_pp?: number | null;
  risk_velocity_pp_month?: number | null;
  since_baseline_pp?: number | null;
  progress_display?: string | null;
  longitudinal_comparable?: boolean;
  next_follow_up?: string | null;
  follow_up_status?: string | null;
  follow_up_id?: string | null;
  follow_up_overdue_days?: number | null;
  visits: ProfileVisit[];
  model_warning?: string | null;
  model_is_demo?: boolean;
  display_semantics?: Record<string, unknown> | null;
  synthetic_data?: boolean;
  data_quality?: Record<string, unknown> | null;
  data_quality_label?: string | null;
  modalities?: {
    anthropometric: ModalityCount;
    socioeconomic: ModalityCount;
    dietary: ModalityCount;
    maternal_child_health: ModalityCount;
  } | null;
  latest_inputs?: Record<string, Record<string, unknown>> | null;
  clinician_review?: ClinicianReview | null;
  model?: {
    key: string;
    version: string;
    label: string;
    architecture: string;
    embedding_dimension: number;
    embedding_space_id: string;
    calibration_version?: string | null;
    feature_schema_version?: string | null;
    is_demo?: boolean;
    status?: string;
  } | null;
  alerts: ProfileAlert[];
  notes: { id: string; body: string; created_at: string; author_id?: string }[];
};

export const PROFILE_TABS = ["overview", "visits", "progress", "notes", "ai"] as const;
export type ProfileTab = (typeof PROFILE_TABS)[number];

export const TAB_LABELS: Record<ProfileTab, string> = {
  overview: "Overview",
  visits: "Visits",
  progress: "Progress & Trajectory",
  notes: "Clinical Notes",
  ai: "AI Details",
};

export function progressLabel(display?: string | null, comparable = true): string {
  if (!comparable || display === "incompatible_model") return "Longitudinal comparison unavailable";
  if (!display || display === "not_available") return "Not available";
  if (display === "insufficient_history" || display === "baseline" || display === "unknown") {
    return "Insufficient history";
  }
  if (display === "stagnating") return "Limited improvement";
  if (display === "improving") return "Improving";
  if (display === "deteriorating") return "Deteriorating";
  if (display === "stable") return "Stable";
  return display.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function reviewLabel(status?: string | null): string {
  if (status === "REVIEWED") return "Reviewed";
  if (status === "AWAITING_REVIEW") return "Awaiting review";
  if (status === "IN_REVIEW") return "In review";
  if (status === "DISAGREED") return "Disagreed";
  if (status === "FURTHER_ASSESSMENT") return "Further assessment required";
  if (status === "NOT_REQUIRED") return "Not required";
  return status ? status.replaceAll("_", " ") : "—";
}

export function formatPp(value?: number | null): string {
  if (value === null || value === undefined) return "Not available";
  const abs = Math.abs(value);
  const n = Number.isInteger(abs) ? String(abs) : abs.toFixed(1).replace(/\.0$/, "");
  return `${value > 0 ? "+" : value < 0 ? "−" : ""}${n} pp`;
}

export function formatRv(value?: number | null, comparable = true): string {
  if (!comparable) return "Not available";
  if (value === null || value === undefined) return "Not available";
  return `${formatPp(value)}/month`;
}

export function measurementDelta(current?: number | null, previous?: number | null): number | null {
  if (current == null || previous == null) return null;
  return Math.round((current - previous) * 10) / 10;
}

export function visitProbabilityDeltaPp(current?: number | null, previous?: number | null): number | null {
  if (current == null || previous == null) return null;
  return Math.round((current - previous) * 1000) / 10;
}

export const TREND_CONDITIONS = ["Underweight", "Stunting", "MAM", "SAM"] as const;
export type TrendCondition = (typeof TREND_CONDITIONS)[number];

export function conditionProbability(
  source?: {
    risk?: number | null;
    predicted_malnutrition_type?: string | null;
    ga_rgca?: {
      underweight_probability?: number;
      stunting_probability?: number;
      mam_probability?: number;
      sam_probability?: number;
    } | null;
  } | null,
  condition?: string | null,
): number | null {
  const ga = source?.ga_rgca;
  if (condition === "Underweight") return ga?.underweight_probability ?? null;
  if (condition === "Stunting") return ga?.stunting_probability ?? null;
  if (condition === "MAM") return ga?.mam_probability ?? null;
  if (condition === "SAM") return ga?.sam_probability ?? null;
  return null;
}

export function primaryTypeProbability(
  source?: {
    risk?: number | null;
    predicted_malnutrition_type?: string | null;
    status?: string | null;
    ga_rgca?: {
      predicted_malnutrition_type?: string | null;
      underweight_probability?: number;
      stunting_probability?: number;
      mam_probability?: number;
      sam_probability?: number;
    } | null;
  } | null,
): number | null {
  const type = displayedMalnutritionType(source);
  const matched = conditionProbability(source, type);
  if (matched != null) return matched;
  return source?.risk ?? null;
}

export function sameConditionDelta(
  current?: Parameters<typeof conditionProbability>[0],
  previous?: Parameters<typeof conditionProbability>[0],
  condition?: string | null,
): number | null {
  const type = condition || displayedMalnutritionType(current);
  if (!type || type === "Normal") return null;
  return visitProbabilityDeltaPp(conditionProbability(current, type), conditionProbability(previous, type));
}

export function defaultTrendCondition(source?: Parameters<typeof displayedMalnutritionType>[0]): TrendCondition {
  const type = displayedMalnutritionType(source);
  if (type === "Underweight" || type === "Stunting" || type === "MAM" || type === "SAM") return type;
  return "Stunting";
}

export function visitBinding(visit?: ProfileVisit | null, dob?: string | null, fallbackAge = 0) {
  return {
    visit_number: visit?.visit_number ?? null,
    visit_date: visit?.visit_date ?? null,
    age_months: ageMonthsAtVisit(dob, visit?.visit_date, fallbackAge),
    height_cm: visit?.measurements?.height_cm ?? null,
    weight_kg: visit?.measurements?.weight_kg ?? null,
    status: displayedMalnutritionType(visit?.prediction) ?? null,
    risk: visit?.prediction?.risk ?? null,
  };
}

/** Convert stored visit risk_velocity (0–1 scale per month) to percentage points. */
export function riskVelocityPpMonth(raw?: number | null): number | null {
  if (raw == null) return null;
  return Math.round(raw * 1000) / 10;
}

/** Calendar-month age at a visit, from stored DOB and visit date. Does not invent measurements. */
export function ageMonthsAtVisit(dob?: string | null, visitDate?: string | null, fallback = 0): number {
  if (!dob || !visitDate) return fallback;
  const birth = dob.slice(0, 10);
  const visit = visitDate.slice(0, 10);
  if (birth.length < 7 || visit.length < 7) return fallback;
  const birthYear = Number(birth.slice(0, 4));
  const birthMonth = Number(birth.slice(5, 7));
  const visitYear = Number(visit.slice(0, 4));
  const visitMonth = Number(visit.slice(5, 7));
  if ([birthYear, birthMonth, visitYear, visitMonth].some((n) => Number.isNaN(n))) return fallback;
  return Math.max(0, (visitYear - birthYear) * 12 + (visitMonth - birthMonth));
}

const ATTENTION_ALERT_STATUSES = new Set(["OPEN", "ACKNOWLEDGED", "IN_REVIEW"]);

/** Prefer OPEN, then ACKNOWLEDGED / IN_REVIEW — actionable clinical attention. */
export function openAlert(profile: ChildProfile): ProfileAlert | undefined {
  const actionable = profile.alerts.filter((a) => ATTENTION_ALERT_STATUSES.has(a.status));
  return (
    actionable.find((a) => a.status === "OPEN") ??
    actionable.find((a) => a.status === "ACKNOWLEDGED") ??
    actionable.find((a) => a.status === "IN_REVIEW")
  );
}

/** Display the backend overall type. Does not derive Underweight or Stunting positivity. */
export function displayedMalnutritionType(
  source?: {
    status?: string | null;
    current_status?: string | null;
    predicted_malnutrition_type?: string | null;
    ga_rgca?: { predicted_malnutrition_type?: string | null } | null;
  } | null,
): string | undefined {
  const fromHead = source?.ga_rgca?.predicted_malnutrition_type;
  if (fromHead) return fromHead;
  if (source?.predicted_malnutrition_type) return source.predicted_malnutrition_type;
  return source?.status ?? source?.current_status ?? undefined;
}

/** All positive model conditions. A single stored type is used when the list is absent. */
export function displayedConditionList(
  source?: {
    status?: string | null;
    current_status?: string | null;
    predicted_malnutrition_type?: string | null;
    detected_conditions?: string[] | null;
    ga_rgca?: { predicted_malnutrition_type?: string | null; detected_conditions?: string[] | null } | null;
  } | null,
): string[] {
  const detected = source?.ga_rgca?.detected_conditions ?? source?.detected_conditions;
  if (Array.isArray(detected) && detected.length > 0) return detected;
  const single = displayedMalnutritionType(source);
  return single ? [single] : [];
}

export function predictedVisits(profile: ChildProfile): ProfileVisit[] {
  return profile.visits.filter((v) => v.prediction?.risk != null);
}

export function probabilitySeries(profile: ChildProfile, condition?: TrendCondition) {
  return predictedVisits(profile).map((v) => {
    const selected = conditionProbability(v.prediction, condition) ?? (condition ? null : v.prediction!.risk);
    return {
      visit: `V${v.visit_number}`,
      date: v.visit_date,
      probability: selected == null ? null : Math.round(selected * 100),
      underweight: conditionProbability(v.prediction, "Underweight"),
      stunting: conditionProbability(v.prediction, "Stunting"),
      mam: conditionProbability(v.prediction, "MAM"),
      sam: conditionProbability(v.prediction, "SAM"),
      status: displayedMalnutritionType(v.prediction),
      severity: v.prediction?.severity,
      weight: v.measurements?.weight_kg ?? null,
      height: v.measurements?.height_cm ?? null,
      muac: v.measurements?.muac_cm ?? null,
    };
  });
}

export type TrendPoint = ReturnType<typeof probabilitySeries>[number];

export function emptyAssessmentMessage(hasBaseline: boolean): string | null {
  if (hasBaseline) return null;
  return "No baseline nutritional assessment recorded.";
}

export function architectureLabel(value?: string | null): string {
  if (!value) return "—";
  if (value === "multimodal_cross_attention") return "Multimodal Cross-Attention";
  return value.replaceAll("_", " ");
}

export function alertTone(type?: string): "red" | "amber" {
  if (type === "DETERIORATION" || type === "RELAPSE") return "red";
  return "amber";
}

/** Primary UI locations — used to assert the overview does not duplicate metrics. */
export const PRIMARY_LOCATIONS = {
  identity: "header",
  measurements: "clinical-snapshot",
  assessment: "ai-assessment",
  progress: "longitudinal-progress",
  alert: "clinical-attention",
  followUp: "follow-up",
  review: "clinician-review",
  history: "assessment-history",
} as const;
