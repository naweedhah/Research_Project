import { describe, expect, it } from "vitest";
import {
  attentionPriorityRank,
  classifyClinicBoard,
  dedupeAttentionCases,
  filterAttentionCases,
  needsAttentionIds,
  presentAttentionCases,
  summarizeClinicBoard,
  whoComparableTokens,
  type AttentionCase,
  type AttentionQuery,
  type ClinicChildInput,
} from "./clinic-board";
import { assessWhoUndernutrition } from "./who-growth-standards";

function child(partial: Partial<ClinicChildInput> & Pick<ClinicChildInput, "id" | "pseudonymous_id">): ClinicChildInput {
  return {
    age_months: 24,
    sex: "female",
    has_assessment: true,
    ...partial,
  };
}

describe("clinic board grouping", () => {
  it("lists a well-measured child whose 12-month prediction is not Normal", () => {
    const groups = classifyClinicBoard([
      child({
        id: "1",
        pseudonymous_id: "C-1",
        predicted_malnutrition_type: "Stunting",
        measurements: { weight_kg: 13, height_cm: 80 },
      }),
    ]);
    expect(groups.wellTodayPredictedRisk).toHaveLength(1);
    expect(groups.wellTodayPredictedRisk[0].predictedLabel).toBe("Stunting");
    expect(groups.wellTodayPredictedRisk[0].whoLabel).toBe("No undernutrition detected");
    expect(groups.undernourishedTodayDifferentPrediction).toHaveLength(0);
  });

  it("uses the latest visit age, not today's age, for the WHO assessment", () => {
    const groups = classifyClinicBoard([
      child({
        id: "age",
        pseudonymous_id: "C-AGE",
        age_months: 60,
        latest_visit_age_months: 24,
        predicted_malnutrition_type: "Stunting",
        measurements: { weight_kg: 11.8, height_cm: 78 },
      }),
    ]);
    expect(groups.undernourishedTodayDifferentPrediction).toHaveLength(0);
    expect(groups.wellTodayPredictedRisk).toHaveLength(0);
  });

  it("does not list agreement between current stunting and predicted stunting", () => {
    const groups = classifyClinicBoard([
      child({
        id: "2",
        pseudonymous_id: "C-2",
        predicted_malnutrition_type: "Stunting",
        measurements: { weight_kg: 11.8, height_cm: 78 },
      }),
    ]);
    const who = assessWhoUndernutrition({
      ageMonths: 24,
      sex: "female",
      weightKg: 11.8,
      heightCm: 78,
    });
    expect(who?.current_undernutrition_conditions).toContain("Stunting");
    expect(groups.undernourishedTodayDifferentPrediction).toHaveLength(0);
    expect(groups.wellTodayPredictedRisk).toHaveLength(0);
  });

  it("lists current wasting when the prediction is Normal", () => {
    const groups = classifyClinicBoard([
      child({
        id: "3",
        pseudonymous_id: "C-3",
        age_months: 30,
        sex: "female",
        predicted_malnutrition_type: "Normal",
        measurements: { weight_kg: 8.0, height_cm: 80 },
      }),
    ]);
    expect(groups.undernourishedTodayDifferentPrediction.length).toBeGreaterThan(0);
    expect(groups.undernourishedTodayDifferentPrediction[0].predictedLabel).toBe("Normal");
    expect(groups.undernourishedTodayDifferentPrediction[0].whoLabel).toMatch(/Wasting/);
  });

  it("maps WHO wasting to MAM/SAM tokens so a matching prediction is not a mismatch", () => {
    const who = assessWhoUndernutrition({
      ageMonths: 30,
      sex: "female",
      weightKg: 8.0,
      heightCm: 80,
    });
    const tokens = whoComparableTokens(who);
    expect(tokens.some((t) => t === "MAM" || t === "SAM")).toBe(true);
    const predicted = tokens.includes("SAM") ? "SAM" : "MAM";
    const groups = classifyClinicBoard([
      child({
        id: "4",
        pseudonymous_id: "C-4",
        age_months: 30,
        sex: "female",
        predicted_malnutrition_type: predicted,
        measurements: { weight_kg: 8.0, height_cm: 80 },
      }),
    ]);
    expect(groups.undernourishedTodayDifferentPrediction).toHaveLength(0);
  });

  it("lists weight loss of 0.1 kg or more and ignores smaller changes", () => {
    const lost = classifyClinicBoard([
      child({
        id: "5",
        pseudonymous_id: "C-5",
        predicted_malnutrition_type: "Normal",
        measurements: { weight_kg: 10.6, height_cm: 80, previous_weight_kg: 11.0 },
      }),
    ]);
    expect(lost.weightLowerThanLastVisit).toHaveLength(1);
    expect(lost.weightLowerThanLastVisit[0].reason).toMatch(/11\.0 kg → 10\.6 kg/);

    const noise = classifyClinicBoard([
      child({
        id: "6",
        pseudonymous_id: "C-6",
        predicted_malnutrition_type: "Normal",
        measurements: { weight_kg: 11.0, height_cm: 80, previous_weight_kg: 11.05 },
      }),
    ]);
    expect(noise.weightLowerThanLastVisit).toHaveLength(0);
  });

  it("puts each child in one slice of the clinic picture", () => {
    const picture = summarizeClinicBoard([
      child({
        id: "1",
        pseudonymous_id: "C-1",
        predicted_malnutrition_type: "Stunting",
        measurements: { weight_kg: 13, height_cm: 80 },
      }),
      child({
        id: "2",
        pseudonymous_id: "C-2",
        predicted_malnutrition_type: "Stunting",
        measurements: { weight_kg: 11.8, height_cm: 78 },
      }),
    ]);
    expect(picture.children).toBe(2);
    expect(picture.alignment.find((slice) => slice.key === "well-risk")?.count).toBe(1);
    expect(picture.alignment.find((slice) => slice.key === "same")?.count).toBe(1);
    expect(picture.measured.reduce((sum, slice) => sum + slice.count, 0)).toBe(2);
    expect(picture.predicted.reduce((sum, slice) => sum + slice.count, 0)).toBe(2);
  });

  it("skips children without a prediction in the comparison trays", () => {
    const groups = classifyClinicBoard([
      child({
        id: "7",
        pseudonymous_id: "C-7",
        has_assessment: false,
        predicted_malnutrition_type: null,
        measurements: { weight_kg: 13, height_cm: 80 },
      }),
    ]);
    expect(groups.wellTodayPredictedRisk).toHaveLength(0);
    expect(groups.undernourishedTodayDifferentPrediction).toHaveLength(0);
  });
});

function attention(partial: Partial<AttentionCase> & Pick<AttentionCase, "id" | "pseudonymous_id">): AttentionCase {
  return {
    age_months: 24,
    sex: "female",
    whoLabel: "No undernutrition detected",
    predictedLabel: "Stunting",
    reason: "",
    predictedTypeProbability: 0.33,
    weightKg: 10,
    previousWeightKg: null,
    reasons: ["future-risk"],
    ...partial,
  };
}

const openQuery: AttentionQuery = {
  tab: "all",
  search: "",
  predictedType: "all",
  sex: "all",
  ageBand: "all",
  sort: "priority",
};

describe("clinic board attention presentation", () => {
  it("counts a child in two trays once", () => {
    const groups = classifyClinicBoard([
      child({
        id: "overlap",
        pseudonymous_id: "C-O",
        full_name: "Nethmi Silva",
        predicted_malnutrition_type: "Stunting",
        predicted_type_probability: 0.33,
        measurements: { weight_kg: 13, height_cm: 80, previous_weight_kg: 13.5 },
      }),
      child({
        id: "only-risk",
        pseudonymous_id: "C-R",
        predicted_malnutrition_type: "Underweight",
        measurements: { weight_kg: 13, height_cm: 80 },
      }),
    ]);
    expect(groups.wellTodayPredictedRisk.length).toBeGreaterThan(0);
    expect(groups.weightLowerThanLastVisit.map((row) => row.id)).toContain("overlap");
    expect(needsAttentionIds(groups)).toHaveLength(2);
    const merged = dedupeAttentionCases(groups).find((row) => row.id === "overlap");
    expect(merged?.reasons.sort()).toEqual(["future-risk", "weight-decline"]);
  });

  it("orders predicted SAM ahead of MAM, Stunting, and Underweight", () => {
    const rows = [
      attention({ id: "uw", pseudonymous_id: "C-UW", predictedLabel: "Underweight", reasons: ["future-risk"] }),
      attention({ id: "sam", pseudonymous_id: "C-SAM", predictedLabel: "SAM", reasons: ["future-risk"] }),
      attention({ id: "st", pseudonymous_id: "C-ST", predictedLabel: "Stunting", reasons: ["future-risk"] }),
      attention({ id: "mam", pseudonymous_id: "C-MAM", predictedLabel: "MAM", reasons: ["future-risk"] }),
    ];
    const ordered = presentAttentionCases(rows, openQuery).map((row) => row.predictedLabel);
    expect(ordered).toEqual(["SAM", "MAM", "Stunting", "Underweight"]);
    expect(attentionPriorityRank(rows[1])).toBeLessThan(attentionPriorityRank(rows[3]));
    expect(attentionPriorityRank(rows[3])).toBeLessThan(attentionPriorityRank(rows[2]));
    expect(attentionPriorityRank(rows[2])).toBeLessThan(attentionPriorityRank(rows[0]));
  });

  it("places a weight-only case after an acute predicted risk", () => {
    const weightOnly = attention({
      id: "w",
      pseudonymous_id: "C-W",
      predictedLabel: "Normal",
      reasons: ["weight-decline"],
      weightDeltaKg: -0.4,
    });
    const sam = attention({ id: "s", pseudonymous_id: "C-S", predictedLabel: "SAM", reasons: ["future-risk"] });
    expect(attentionPriorityRank(sam)).toBeLessThan(attentionPriorityRank(weightOnly));
    expect(presentAttentionCases([weightOnly, sam], openQuery).map((row) => row.id)).toEqual(["s", "w"]);
  });

  it("searches by pseudonymous id and full name", () => {
    const rows = [
      attention({ id: "1", pseudonymous_id: "C-102", full_name: "Nethmi Silva" }),
      attention({ id: "2", pseudonymous_id: "C-088", full_name: "Harish Rajendran" }),
    ];
    expect(filterAttentionCases(rows, { ...openQuery, search: "c-102" }).map((row) => row.id)).toEqual(["1"]);
    expect(filterAttentionCases(rows, { ...openQuery, search: "nethmi" }).map((row) => row.id)).toEqual(["1"]);
  });

  it("filters by predicted type and age band", () => {
    const rows = [
      attention({ id: "sam", pseudonymous_id: "C-1", predictedLabel: "SAM", age_months: 4 }),
      attention({ id: "st", pseudonymous_id: "C-2", predictedLabel: "Stunting", age_months: 30 }),
    ];
    expect(filterAttentionCases(rows, { ...openQuery, predictedType: "SAM" }).map((row) => row.id)).toEqual(["sam"]);
    expect(filterAttentionCases(rows, { ...openQuery, ageBand: "0-5" }).map((row) => row.id)).toEqual(["sam"]);
    expect(filterAttentionCases(rows, { ...openQuery, ageBand: "24-35" }).map((row) => row.id)).toEqual(["st"]);
  });
});
