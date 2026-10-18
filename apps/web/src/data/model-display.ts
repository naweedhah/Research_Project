/** Centralized model-output display semantics for clinical UI. */

export type ModelDisplaySemantics = {
  model_mode: string;
  clinical_use: boolean;
  is_demo: boolean;
  score_kind: string;
  score_label: string;
  score_description: string;
  score_is_probability: boolean;
  score_is_calibrated: boolean;
  velocity_label: string;
  velocity_description: string;
  prediction_task: string;
  prediction_task_label: string;
  projection_version: string | null;
  projection_label: string;
  projection_description: string;
  confidence_label: string;
  confidence_is_calibrated: boolean;
  banner_title: string;
  banner_subtitle: string;
  report_disclaimer: string;
  alert_rule_note: string;
};

export const V4_DISPLAY_SEMANTICS: ModelDisplaySemantics = {
  model_mode: "ga_rgca_v4_rsl",
  clinical_use: false,
  is_demo: false,
  score_kind: "highest_condition_probability",
  score_label: "Highest Predicted Condition Risk",
  score_description:
    "Highest of the Underweight, Stunting, MAM, and SAM probabilities from the 12-month GA-RGCA prediction. Clinical review required.",
  score_is_probability: true,
  score_is_calibrated: true,
  velocity_label: "Risk Velocity",
  velocity_description:
    "Visit-to-visit change is shown only when both visits used the same 12-month GA-RGCA prediction.",
  prediction_task: "twelve_month_nutritional_risk",
  prediction_task_label: "12-month GA-RGCA prediction",
  projection_version: "ga-rgca-v4-fused-latent-v1",
  projection_label: "Fused latent representation",
  projection_description: "Coordinates from the GA-RGCA v4 fused latent vector. This is not anatomical imaging.",
  confidence_label: "Ensemble uncertainty",
  confidence_is_calibrated: false,
  banner_title: "RESEARCH MODEL",
  banner_subtitle: "GA-RGCA-v4-Rolling-RSL · Research decision-support prototype — clinician confirmation required.",
  report_disclaimer: "Research decision-support prototype. Clinician confirmation required.",
  alert_rule_note: "Generated from the 12-month GA-RGCA prediction",
};

type SemanticsSource = {
  display_semantics?: Partial<ModelDisplaySemantics> | null;
  model_is_demo?: boolean | null;
  model?: { is_demo?: boolean | null } | null;
  score_label?: string | null;
  probability_label?: string | null;
  velocity_label?: string | null;
};

function clinicLabel(value: string | null | undefined, fallback: string) {
  if (!value || /demo|dummy|synthetic|demonstration/i.test(value)) return fallback;
  return value;
}

/** Prefer backend display semantics. The only fallback is the v4 research label set. */
export function getModelOutputDisplayMetadata(source?: SemanticsSource | null): ModelDisplaySemantics {
  const incoming = source?.display_semantics?.score_label
    ? ({ ...V4_DISPLAY_SEMANTICS, ...source.display_semantics } as ModelDisplaySemantics)
    : null;
  const base = incoming ?? V4_DISPLAY_SEMANTICS;
  return {
    ...base,
    is_demo: false,
    clinical_use: false,
    score_label: clinicLabel(source?.score_label ?? source?.probability_label ?? base.score_label, "12-month GA-RGCA prediction"),
    score_description: clinicLabel(base.score_description, "12-month GA-RGCA prediction from the measurements recorded at this visit. Clinical review required."),
    velocity_label: clinicLabel(source?.velocity_label ?? base.velocity_label, "Risk Velocity"),
    velocity_description: clinicLabel(base.velocity_description, "Visit-to-visit change in the 12-month GA-RGCA prediction."),
    prediction_task_label: clinicLabel(base.prediction_task_label, "12-month GA-RGCA prediction"),
    projection_label: clinicLabel(base.projection_label, "Fused latent representation"),
    projection_description: clinicLabel(base.projection_description, "Coordinates from the GA-RGCA v4 fused latent vector."),
    confidence_label: clinicLabel(base.confidence_label, "Ensemble uncertainty"),
    banner_title: clinicLabel(base.banner_title, "RESEARCH MODEL"),
    banner_subtitle: clinicLabel(base.banner_subtitle, "Research decision-support prototype. Clinician confirmation required."),
    report_disclaimer: clinicLabel(base.report_disclaimer, "Research decision-support prototype. Clinician confirmation required."),
    alert_rule_note: clinicLabel(base.alert_rule_note, "Generated from the 12-month GA-RGCA prediction"),
  };
}
