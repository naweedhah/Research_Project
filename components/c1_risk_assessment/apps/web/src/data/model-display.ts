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

export const DEMO_DISPLAY_SEMANTICS: ModelDisplaySemantics = {
  model_mode: "demo",
  clinical_use: false,
  is_demo: true,
  score_kind: "model_assessed_probability",
  score_label: "Model-assessed probability",
  score_description:
    "Model-assessed probability from the measurements recorded at this visit. Clinical review required.",
  score_is_probability: true,
  score_is_calibrated: false,
  velocity_label: "Risk velocity",
  velocity_description:
    "Visit-to-visit change in model-assessed probability, adjusted for elapsed time. Clinical review required.",
  prediction_task: "current_status",
  prediction_task_label: "Current nutritional assessment",
  projection_version: null,
  projection_label: "Model trajectory",
  projection_description:
    "Visit-to-visit model trajectory from recorded assessments. It is not anatomical imaging.",
  confidence_label: "Model confidence",
  confidence_is_calibrated: false,
  banner_title: "Clinical review required",
  banner_subtitle: "AI-assisted assessment. Clinical review required.",
  report_disclaimer: "AI-assisted assessment. Clinical review required.",
  alert_rule_note: "Generated from the model-assessed probability",
};

export const RESEARCH_DISPLAY_SEMANTICS: ModelDisplaySemantics = {
  model_mode: "research",
  clinical_use: false,
  is_demo: false,
  score_kind: "research_model_score",
  score_label: "Model-Assessed Probability",
  score_description:
    "Research model output. Clinical review required. Not clinically validated for care decisions.",
  score_is_probability: true,
  score_is_calibrated: false,
  velocity_label: "Risk Velocity",
  velocity_description:
    "Visit-to-visit change in model-assessed probability adjusted for elapsed time. Clinical review required.",
  prediction_task: "current_status",
  prediction_task_label: "Current-status classification",
  projection_version: null,
  projection_label: "Model latent projection",
  projection_description: "2D projection of the model latent representation. Research visualization only.",
  confidence_label: "Model confidence",
  confidence_is_calibrated: false,
  banner_title: "RESEARCH MODEL",
  banner_subtitle: "Clinical review required",
  report_disclaimer: "RESEARCH MODEL — Clinical review required · Not clinically validated",
  alert_rule_note: "Research model alert rule",
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

/** Prefer backend display_semantics; fall back from is_demo flags. Never invent clinical validation. */
export function getModelOutputDisplayMetadata(source?: SemanticsSource | null): ModelDisplaySemantics {
  const incoming = source?.display_semantics?.score_label
    ? ({ ...DEMO_DISPLAY_SEMANTICS, ...source.display_semantics } as ModelDisplaySemantics)
    : null;
  const demo = Boolean(source?.model_is_demo ?? source?.model?.is_demo ?? true);
  const base = incoming ?? (demo ? DEMO_DISPLAY_SEMANTICS : RESEARCH_DISPLAY_SEMANTICS);
  return {
    ...base,
    score_label: clinicLabel(source?.score_label ?? source?.probability_label ?? base.score_label, "Model-assessed probability"),
    score_description: clinicLabel(base.score_description, "Model-assessed probability from the measurements recorded at this visit. Clinical review required."),
    velocity_label: clinicLabel(source?.velocity_label ?? base.velocity_label, "Risk velocity"),
    velocity_description: clinicLabel(base.velocity_description, "Visit-to-visit change in model-assessed probability, adjusted for elapsed time. Clinical review required."),
    prediction_task_label: clinicLabel(base.prediction_task_label, "Current nutritional assessment"),
    projection_label: clinicLabel(base.projection_label, "Model trajectory"),
    projection_description: clinicLabel(base.projection_description, "Visit-to-visit model trajectory from recorded assessments."),
    confidence_label: clinicLabel(base.confidence_label, "Model confidence"),
    banner_title: clinicLabel(base.banner_title, "Clinical review required"),
    banner_subtitle: clinicLabel(base.banner_subtitle, "AI-assisted assessment. Clinical review required."),
    report_disclaimer: clinicLabel(base.report_disclaimer, "AI-assisted assessment. Clinical review required."),
    alert_rule_note: clinicLabel(base.alert_rule_note, "Generated from the model-assessed probability"),
  };
}
