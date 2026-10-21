import { describe, expect, it } from "vitest";
import {
  ACUTE_MALNUTRITION_STATUSES,
  PREDICTED_MALNUTRITION_TYPES,
  displayedMalnutritionType,
  formatHighestConditionRisk,
  highestConditionRisk,
  architectureLabel,
  primaryTypeProbability,
  primaryTypeProbabilityLabel,
  predictedTypeChipProbability,
  runtimeModeLabel,
  probabilitySeries,
  sameConditionDelta,
  visitBinding,
  normalCategoryProbability,
  type ChildProfile,
  type PredictedMalnutritionType,
  type AcuteMalnutritionStatus,
} from "./child-profile";

describe("malnutrition type display", () => {
  it("supports the five overall types and a separate acute union", () => {
    const overall: PredictedMalnutritionType[] = ["Normal", "Underweight", "Stunting", "MAM", "SAM"];
    const acute: AcuteMalnutritionStatus[] = ["Normal", "MAM", "SAM"];
    expect(PREDICTED_MALNUTRITION_TYPES).toEqual(overall);
    expect(ACUTE_MALNUTRITION_STATUSES).toEqual(acute);
    expect(PREDICTED_MALNUTRITION_TYPES).toContain("Underweight");
    expect(PREDICTED_MALNUTRITION_TYPES).toContain("Stunting");
    expect(ACUTE_MALNUTRITION_STATUSES).not.toContain("Stunting");
    expect(ACUTE_MALNUTRITION_STATUSES).not.toContain("Underweight");
  });

  it("displays predicted malnutrition type instead of acute status", () => {
    expect(
      displayedMalnutritionType({
        status: "Normal",
        ga_rgca: {
          predicted_malnutrition_type: "Stunting",
          acute_status: "Normal",
        },
      }),
    ).toBe("Stunting");
  });

  it("keeps a demo label when the backend did not send an overall type", () => {
    expect(displayedMalnutritionType({ status: "wasting" })).toBe("wasting");
  });

  it("uses the backend type on the longitudinal series", () => {
    const profile = {
      visits: [
        {
          id: "v1",
          visit_number: 1,
          visit_date: "2026-01-01",
          prediction: {
            status: "Normal",
            risk: 0.66,
            ga_rgca: { predicted_malnutrition_type: "Stunting", acute_status: "Normal" },
          },
        },
      ],
    } as ChildProfile;
    expect(probabilitySeries(profile)[0].status).toBe("Stunting");
  });

  it("uses the primary type probability for body RISK", () => {
    expect(
      primaryTypeProbability({
        status: "Stunting",
        risk: 0.66,
        ga_rgca: {
          predicted_malnutrition_type: "Stunting",
          underweight_probability: 0,
          stunting_probability: 0.66,
          mam_probability: 0.01,
          sam_probability: 0,
        },
      }),
    ).toBe(0.66);
    expect(
      primaryTypeProbability({
        status: "Normal",
        risk: 0.05,
        ga_rgca: {
          predicted_malnutrition_type: "Normal",
          underweight_probability: 0.004,
          stunting_probability: 0.05,
          mam_probability: 0.03,
          sam_probability: 0.004,
        },
      }),
    ).toBeCloseTo(0.95, 5);
  });

  it("shows Normal as the residual of the highest malnutrition head", () => {
    expect(
      normalCategoryProbability({
        underweight_probability: 0.004,
        stunting_probability: 0.05,
        mam_probability: 0.03,
        sam_probability: 0.004,
      }),
    ).toBeCloseTo(0.95, 5);
    expect(normalCategoryProbability({ underweight_probability: 0.33, stunting_probability: 0, mam_probability: 0, sam_probability: 0 })).toBeCloseTo(0.67, 5);
    expect(normalCategoryProbability(null)).toBeNull();
  });

  it("plots the selected condition across visits", () => {
    const profile = {
      visits: [
        {
          id: "v1",
          visit_number: 1,
          visit_date: "2026-01-01",
          prediction: { risk: 0.23, ga_rgca: { predicted_malnutrition_type: "Underweight", underweight_probability: 0.23, stunting_probability: 0.1, mam_probability: 0, sam_probability: 0 } },
        },
        {
          id: "v2",
          visit_number: 2,
          visit_date: "2026-04-01",
          prediction: { risk: 0.66, ga_rgca: { predicted_malnutrition_type: "Stunting", underweight_probability: 0.05, stunting_probability: 0.66, mam_probability: 0.01, sam_probability: 0 } },
        },
      ],
    } as ChildProfile;
    expect(probabilitySeries(profile, "Stunting").map((row) => row.probability)).toEqual([10, 66]);
    expect(probabilitySeries(profile, "Underweight").map((row) => row.probability)).toEqual([23, 5]);
  });

  it("binds age, height, weight, visit number and prediction from the same visit", () => {
    const visit = {
      id: "v2",
      visit_number: 2,
      visit_date: "2026-04-14T09:00:00",
      measurements: { height_cm: 80, weight_kg: 10 },
      prediction: { status: "Normal", ga_rgca: { predicted_malnutrition_type: "Stunting" } },
    };
    const bound = visitBinding(visit, "2024-04-14", 99);
    expect(bound).toMatchObject({
      visit_number: 2,
      height_cm: 80,
      weight_kg: 10,
      status: "Stunting",
      age_months: 24,
    });
  });

  describe("predicted type probability vs highest condition risk", () => {
    const normalChild = {
      risk: 0.05,
      ga_rgca: {
        predicted_malnutrition_type: "Normal",
        underweight_probability: 0.02,
        stunting_probability: 0.05,
        mam_probability: 0.01,
        sam_probability: 0.0,
      },
    };

    it("pairs Normal with the residual and names the leading condition for the stored risk", () => {
      expect(primaryTypeProbability(normalChild)).toBeCloseTo(0.95);
      expect(primaryTypeProbabilityLabel(normalChild)).toBe("Normal probability");
      expect(predictedTypeChipProbability(normalChild)).toBeNull();
      expect(highestConditionRisk(normalChild)).toEqual({ condition: "Stunting", probability: 0.05 });
      expect(formatHighestConditionRisk(normalChild)).toBe("Stunting 5%");
    });

    it("the two numbers are complementary for a Normal prediction", () => {
      const residual = primaryTypeProbability(normalChild)!;
      const highest = highestConditionRisk(normalChild).probability!;
      expect(residual + highest).toBeCloseTo(1);
    });

    it("pairs a condition type with its own head and keeps the highest risk separate", () => {
      const stunted = {
        risk: 0.66,
        ga_rgca: {
          predicted_malnutrition_type: "Stunting",
          underweight_probability: 0.7,
          stunting_probability: 0.66,
          mam_probability: 0.01,
          sam_probability: 0,
        },
      };
      expect(primaryTypeProbability(stunted)).toBe(0.66);
      expect(predictedTypeChipProbability(stunted)).toBe(0.66);
      expect(highestConditionRisk(stunted)).toEqual({ condition: "Underweight", probability: 0.7 });
    });

    it("uses backend fields when per-condition heads are absent (worklist rows)", () => {
      const row = {
        current_status: "Normal",
        predicted_malnutrition_type: "Normal",
        current_risk: 0.05,
        predicted_type_probability: 0.95,
        highest_risk_condition: "Stunting",
        highest_risk_probability: 0.05,
      };
      expect(primaryTypeProbability(row)).toBe(0.95);
      expect(formatHighestConditionRisk(row)).toBe("Stunting 5%");
    });

    it("derives the Normal residual from current_risk when only the leading condition is known", () => {
      const row = { current_status: "Normal", current_risk: 0.05, highest_risk_condition: "Stunting" };
      expect(primaryTypeProbability(row)).toBeCloseTo(0.95);
    });

    it("falls back to the stored score for demo-mode predictions", () => {
      const demo = { status: "Underweight", risk: 0.42 };
      expect(primaryTypeProbability(demo)).toBe(0.42);
      expect(highestConditionRisk(demo)).toEqual({ condition: null, probability: 0.42 });
      expect(formatHighestConditionRisk(demo)).toBe("42%");
    });

    it("Normal residual delta is comparable across visits", () => {
      const previous = { ...normalChild, ga_rgca: { ...normalChild.ga_rgca, stunting_probability: 0.1 } };
      expect(sameConditionDelta(normalChild, previous)).toBe(5);
    });

    it("does not present PYTORCH as the professor-facing architecture", () => {
      expect(architectureLabel("PYTORCH")).toBe("GA-RGCA v4 Rolling SuperLearner");
      expect(runtimeModeLabel("PYTORCH")).toBe("GA-RGCA v4 Rolling SuperLearner");
    });
  });
});