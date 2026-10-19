import { describe, expect, it } from "vitest";
import { applicabilityState, dataQualityState, measurementChange, predictionLabel, uncertaintyState, whoLabelForVisit } from "./clinical-selectors";
import type { ProfilePrediction, ProfileVisit } from "./child-profile";

const prediction = {
  status: "Normal",
  severity: "Normal",
  risk: 0.2,
  ga_rgca: {
    predicted_malnutrition_type: "Stunting",
    uncertainty_flag: false,
    out_of_distribution_flag: true,
    latent_distance: 1.2345,
  },
} as unknown as ProfilePrediction;

describe("clinical selectors", () => {
  it("words the stored uncertainty flag for clinicians without changing it", () => {
    expect(uncertaintyState(prediction).label).toBe("Low review signal");
    expect(uncertaintyState({ ...prediction, ga_rgca: { ...prediction.ga_rgca, uncertainty_flag: true } } as ProfilePrediction).label).toBe(
      "Additional clinician review recommended",
    );
    expect(uncertaintyState(null).flagged).toBeNull();
  });

  it("words the stored applicability flag and keeps the latent distance", () => {
    const state = applicabilityState(prediction);
    expect(state.label).toBe("Outside internal reference range");
    expect(state.detail).toContain("1.23");
    expect(state.detail).toContain("not externally validated");
  });

  it("formats measurement change with sign and unit", () => {
    expect(measurementChange(9.4, 9.0)?.text).toBe("+0.4 kg");
    expect(measurementChange(72.1, 72.6, "cm")?.text).toBe("-0.5 cm");
    expect(measurementChange(null, 1)).toBeNull();
  });

  it("maps WHO no-undernutrition to Normal and missing measurements to Not assessed", () => {
    const profile = { date_of_birth: "2024-01-01", age_months: 18, sex: "female" };
    const visit = { visit_date: "2025-07-01", measurements: { weight_kg: 10.2, height_cm: 80 } } as unknown as ProfileVisit;
    expect(whoLabelForVisit(profile, visit)).toBe("Normal");
    expect(whoLabelForVisit(profile, { visit_date: "2025-07-01", measurements: {} } as unknown as ProfileVisit)).toBe("Not assessed");
  });

  it("uses the displayed malnutrition type for the prediction label", () => {
    expect(predictionLabel(prediction)).toContain("Stunting");
    expect(predictionLabel(null)).toBe("No prediction stored");
  });

  it("reads the backend data-quality label only", () => {
    expect(dataQualityState({ data_quality_label: "complete", data_quality: null }).label).toBe("Complete");
    expect(dataQualityState({ data_quality_label: "review_required", data_quality: { blocking_errors: [{ message: "Height missing" }] } }).detail).toBe("Height missing");
    expect(dataQualityState({ data_quality_label: null, data_quality: null }).tone).toBe("muted");
  });
});
