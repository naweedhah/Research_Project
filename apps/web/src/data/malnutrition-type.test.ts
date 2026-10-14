import { describe, expect, it } from "vitest";
import {
  ACUTE_MALNUTRITION_STATUSES,
  PREDICTED_MALNUTRITION_TYPES,
  displayedMalnutritionType,
  probabilitySeries,
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
});