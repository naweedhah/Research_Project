import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  PRIMARY_LOCATIONS,
  PROFILE_TABS,
  TAB_LABELS,
  ageMonthsAtVisit,
  emptyAssessmentMessage,
  formatPp,
  formatRv,
  measurementDelta,
  openAlert,
  probabilitySeries,
  progressLabel,
  reviewLabel,
  visitProbabilityDeltaPp,
  riskVelocityPpMonth,
  type ChildProfile,
} from "./child-profile";

function visit(n: number, risk: number, extra: Partial<ChildProfile["visits"][number]> = {}) {
  return {
    id: `v${n}`,
    visit_number: n,
    visit_date: `2026-0${n}-01T00:00:00Z`,
    prediction: { status: "wasting", severity: "moderate", risk },
    measurements: { weight_kg: 8 + n, height_cm: 70 + n, muac_cm: 12 },
    review_status: n === 4 ? "AWAITING_REVIEW" : "REVIEWED",
    ...extra,
  };
}

const profile: ChildProfile = {
  id: "id",
  pseudonymous_id: "C-1005",
  age_months: 17,
  sex: "male",
  visits: [visit(1, 0.78), visit(2, 0.49), visit(3, 0.33), visit(4, 0.58)],
  alerts: [
    {
      id: "a1",
      type: "DETERIORATION",
      severity: "HIGH",
      status: "OPEN",
      message: "Model-assessed probability increased",
      headline: "Deterioration detected",
      trigger_value: { previous_risk: 0.33, current_risk: 0.58 },
    },
  ],
  notes: [],
  risk_change_pp: 25,
  risk_velocity_pp_month: -12.4,
  progress_display: "deteriorating",
  longitudinal_comparable: true,
  model_is_demo: true,
};

describe("child profile view model", () => {
  it("assigns each metric a single primary location", () => {
    expect(PRIMARY_LOCATIONS.measurements).toBe("clinical-snapshot");
    expect(PRIMARY_LOCATIONS.assessment).toBe("ai-assessment");
    expect(PRIMARY_LOCATIONS.progress).toBe("longitudinal-progress");
    expect(new Set(Object.values(PRIMARY_LOCATIONS)).size).toBe(Object.keys(PRIMARY_LOCATIONS).length);
  });

  it("formats probability change as percentage points not percent", () => {
    expect(formatPp(25)).toBe("+25 pp");
    expect(formatPp(-20)).toBe("−20 pp");
    expect(formatPp(null)).toBe("Not available");
  });

  it("does not fabricate risk velocity", () => {
    expect(formatRv(null, true)).toBe("Not available");
    expect(formatRv(-12.4, true)).toBe("−12.4 pp/month");
    expect(formatRv(1, false)).toBe("Not available");
  });

  it("labels a single visit as insufficient history instead of stable", () => {
    expect(progressLabel("stable", true)).toBe("Stable");
    expect(progressLabel("insufficient_history", true)).toBe("Insufficient history");
    expect(progressLabel("baseline", true)).toBe("Insufficient history");
    expect(progressLabel("improving", false)).toBe("Longitudinal comparison unavailable");
  });

  it("keeps nutritional status separate from clinician review state", () => {
    expect(reviewLabel("AWAITING_REVIEW")).toBe("Awaiting review");
    expect(reviewLabel("REVIEWED")).toBe("Reviewed");
    expect(reviewLabel("AWAITING_REVIEW")).not.toBe("Critical");
    expect(reviewLabel("REVIEWED")).not.toBe("Normal");
  });

  it("builds chart series only from stored visit probabilities", () => {
    const series = probabilitySeries(profile);
    expect(series.map((s) => s.probability)).toEqual([78, 49, 33, 58]);
    expect(series).toHaveLength(profile.visits.length);
  });

  it("does not invent a chart point when a visit has no prediction", () => {
    const sparse: ChildProfile = {
      ...profile,
      visits: [visit(1, 0.5), { id: "x", visit_number: 2, visit_date: "2026-02-01", prediction: null }],
    };
    expect(probabilitySeries(sparse)).toHaveLength(1);
  });

  it("uses previous measurement only when both values exist", () => {
    expect(measurementDelta(9.9, 9.6)).toBe(0.3);
    expect(measurementDelta(9.9, null)).toBeNull();
  });

  it("computes visit probability change as percentage points from stored risks", () => {
    expect(visitProbabilityDeltaPp(0.58, 0.33)).toBe(25);
    expect(visitProbabilityDeltaPp(0.33, 0.58)).toBe(-25);
    expect(visitProbabilityDeltaPp(0.58, null)).toBeNull();
  });

  it("converts stored risk velocity to percentage points without inventing a value", () => {
    expect(riskVelocityPpMonth(null)).toBeNull();
    expect(riskVelocityPpMonth(-0.124)).toBe(-12.4);
    expect(riskVelocityPpMonth(0.02)).toBe(2);
  });

  it("ages the child from visit date and DOB rather than inventing an age", () => {
    expect(ageMonthsAtVisit("2025-03-08", "2026-06-12")).toBe(15);
    expect(ageMonthsAtVisit("2025-03-08", "2026-02-01")).toBe(11);
    expect(ageMonthsAtVisit(null, "2026-06-12", 17)).toBe(17);
  });

  it("surfaces open, acknowledged, and in-review alerts", () => {
    expect(openAlert(profile)?.headline).toBe("Deterioration detected");
    expect(openAlert({ ...profile, alerts: [{ ...profile.alerts[0], status: "RESOLVED" }] })).toBeUndefined();
    expect(openAlert({ ...profile, alerts: [{ ...profile.alerts[0], status: "ACKNOWLEDGED" }] })?.status).toBe("ACKNOWLEDGED");
    expect(openAlert({ ...profile, alerts: [{ ...profile.alerts[0], status: "IN_REVIEW" }] })?.status).toBe("IN_REVIEW");
  });

  it("uses factual empty-assessment copy and never fabricates Stable for V0", () => {
    expect(emptyAssessmentMessage(false)).toBe("No baseline nutritional assessment recorded.");
    expect(emptyAssessmentMessage(true)).toBeNull();
    expect(progressLabel("insufficient_history")).not.toBe("Stable");
  });

  it("exposes profile tabs without duplicating overview content contracts", () => {
    expect(PROFILE_TABS).toEqual(["overview", "visits", "progress", "notes", "ai"]);
    expect(TAB_LABELS.overview).toBe("Overview");
    expect(TAB_LABELS.progress).toBe("Progress & Trajectory");
    expect(TAB_LABELS.ai).toBe("AI Details");
  });
});

describe("child profile page markup contract", () => {
  const src = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "../components/component4/child-profile-view.tsx"), "utf8");
  const hud = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "../components/component4/child-model-hud.tsx"), "utf8");

  it("renders each primary clinical block once", () => {
    expect(src.match(/id="clinical-snapshot"/g)).toHaveLength(1);
    expect(src.match(/id="ai-assessment"/g)).toHaveLength(1);
    expect(hud).not.toMatch(/id="clinical-snapshot"/);
    expect(hud).not.toMatch(/sectionId: "ai-assessment"/);
    expect(src.match(/id="longitudinal-progress"/g)).toHaveLength(1);
    expect(src.match(/id="clinician-review"/g)).toHaveLength(1);
    expect(src.match(/id="follow-up"/g)).toHaveLength(1);
    expect(src.match(/id="assessment-history"/g)).toHaveLength(1);
    expect(src.match(/id="advanced-ai"/g)).toHaveLength(1);
    expect(src).toMatch(/AdvancedAiSummary/);
    expect(src).toMatch(/LatentTrajectory/);
    expect(src).toMatch(/latent-trajectory-title/);
    expect(src).toMatch(/ExplainabilityTrigger/);
    expect(src).not.toMatch(/Explainability component not connected/);
    const explain = readFileSync(
      path.join(path.dirname(fileURLToPath(import.meta.url)), "../components/component4/explainability-dialog.tsx"),
      "utf8",
    );
    expect(explain).not.toMatch(/Request Component 2 explanation/);
    expect(explain).not.toMatch(/Component 2/);
    expect(explain).not.toMatch(/Healthy Zone/);
    expect(explain).not.toMatch(/featureImportance/);
    expect(hud).toMatch(/valueTestId: "primary-probability"/);
    expect(hud).toMatch(/label: "Weight"/);
    expect(hud).toMatch(/label: "Height"/);
    expect(hud).not.toMatch(/label: "MUAC"/);
    expect(hud).toMatch(/label: "Age"/);
    expect(hud).toMatch(/label: "Sex"/);
    expect(hud).not.toMatch(/>\s*Snapshot\s*</);
    expect(hud).not.toMatch(/>\s*Assessment\s*</);
    expect(hud).toMatch(/label: "Status"/);
    expect(hud).toMatch(/scoreLabel/);
    expect(hud).toMatch(/Model-assessed probability/);
    expect(hud).toMatch(/Risk velocity/);
    expect(src).toMatch(/getModelOutputDisplayMetadata/);
    expect(src).toMatch(/semantics\.projection_label/);
    expect(src).toMatch(/semantics\.prediction_task_label/);
    expect(src).not.toMatch(/pca-demo/);
    const display = readFileSync(
      path.join(path.dirname(fileURLToPath(import.meta.url)), "./model-display.ts"),
      "utf8",
    );
    expect(display).toMatch(/Model trajectory/);
    expect(display).toMatch(/Current nutritional assessment/);
  });

  it("does not restore ambiguous visit badges", () => {
    expect(src).not.toMatch(/Critical/);
    expect(src).not.toMatch(/visitActivityStatus/);
  });

  it("places a 3D model and visit snapshot inside the patient stage", () => {
    expect(src).toMatch(/id="patient-stage"/);
    expect(src).toMatch(/ChildModelHud/);
    expect(hud).toMatch(/hud-connector/);
    expect(hud).not.toMatch(/rail-link/);
    expect(src).toMatch(/Visit \{v.visit_number\}/);
    expect(src).toMatch(/Go back/);
  });

  it("does not show a demo-model clinical-use badge", () => {
    expect(src).not.toMatch(/DEMO MODEL/);
    expect(src).not.toMatch(/NOT FOR CLINICAL USE/);
  });
});
