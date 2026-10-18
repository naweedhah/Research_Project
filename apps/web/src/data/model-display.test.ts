import { describe, expect, it } from "vitest";
import { getModelOutputDisplayMetadata, V4_DISPLAY_SEMANTICS } from "./model-display";

describe("model display semantics", () => {
  it("uses the 12-month GA-RGCA label for every clinic surface", () => {
    const meta = getModelOutputDisplayMetadata();
    expect(meta.score_label).toBe("Highest Predicted Condition Risk");
    expect(meta.score_kind).toBe("highest_condition_probability");
    expect(meta.velocity_label).toBe("Risk Velocity");
    expect(meta.prediction_task_label).toMatch(/12-month GA-RGCA prediction/i);
    expect(meta.banner_subtitle).toMatch(/GA-RGCA-v4-Rolling-RSL/);
    expect(meta.clinical_use).toBe(false);
    expect(meta.is_demo).toBe(false);
  });

  it("does not switch labels when an old demo flag is still present", () => {
    const meta = getModelOutputDisplayMetadata({ model_is_demo: true });
    expect(meta.is_demo).toBe(false);
    expect(meta.model_mode).toBe("ga_rgca_v4_rsl");
    expect(meta.clinical_use).toBe(false);
  });

  it("prefers backend display_semantics when present", () => {
    const meta = getModelOutputDisplayMetadata({
      display_semantics: {
        ...V4_DISPLAY_SEMANTICS,
        score_label: "Calibrated Malnutrition Probability",
        score_is_probability: true,
        score_is_calibrated: true,
      },
    });
    expect(meta.score_label).toBe("Calibrated Malnutrition Probability");
    expect(meta.score_is_calibrated).toBe(true);
    expect(meta.is_demo).toBe(false);
  });

  it("exports the v4 fallback", () => {
    expect(V4_DISPLAY_SEMANTICS.report_disclaimer).toMatch(/Clinician confirmation required/i);
    expect(V4_DISPLAY_SEMANTICS.model_mode).toBe("ga_rgca_v4_rsl");
  });
});
