import { describe, expect, it } from "vitest";
import {
  ACUTE_MALNUTRITION_STATUSES,
  PREDICTED_MALNUTRITION_TYPES,
  displayedMalnutritionType,
  primaryTypeProbability,
  probabilitySeries,
  visitBinding,
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
});