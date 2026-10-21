import { describe, expect, it } from "vitest";
import {
  DEMO_DISPLAY_SEMANTICS,
  getModelOutputDisplayMetadata,
  RESEARCH_DISPLAY_SEMANTICS,
} from "./model-display";

describe("model display semantics", () => {
  it("uses clinic language for model output labels", () => {
    const meta = getModelOutputDisplayMetadata({ model_is_demo: true });
    expect(meta.score_label).toBe("Model-assessed probability");
    expect(meta.score_kind).toBe("model_assessed_probability");
    expect(meta.velocity_label).toBe("Risk velocity");
    expect(meta.prediction_task_label).toMatch(/Current nutritional assessment/i);
    expect(meta.banner_subtitle).toMatch(/Clinical review required/i);
    expect(meta.projection_label).toMatch(/Model trajectory/);
    expect(meta.clinical_use).toBe(false);
    expect(meta.score_label).not.toMatch(/demo/i);
  });

  it("does not auto-claim clinical validation for research modes", () => {
    const meta = getModelOutputDisplayMetadata({ model_is_demo: false });
    expect(meta.clinical_use).toBe(false);
    expect(meta.banner_title).toBe("RESEARCH MODEL");
    expect(meta.score_label).toBe("Model-Assessed Probability");
    expect(meta.prediction_task_label).toMatch(/Current-status classification/i);
  });

  it("prefers backend display_semantics when present", () => {
    const meta = getModelOutputDisplayMetadata({
      model_is_demo: false,
      display_semantics: {
        ...RESEARCH_DISPLAY_SEMANTICS,
        score_label: "Calibrated Malnutrition Probability",
        score_is_probability: true,
        score_is_calibrated: true,
      },
    });
    expect(meta.score_label).toBe("Calibrated Malnutrition Probability");
    expect(meta.score_is_calibrated).toBe(true);
  });

  it("exports stable demo defaults for UI fallback", () => {
    expect(DEMO_DISPLAY_SEMANTICS.report_disclaimer).toMatch(/Clinical review required/i);
  });
});
