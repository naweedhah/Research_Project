import { describe, expect, it } from "vitest";
import {
  NO_UNDERNUTRITION_LABEL,
  UNDERNUTRITION_Z_CUTOFF,
  assessWhoUndernutrition,
  classifyUndernutrition,
  whoZScores,
} from "./who-growth-standards";

describe("current WHO undernutrition assessment (z-score rules)", () => {
  it("CASE 1: positive and mildly low z-scores -> no undernutrition detected", () => {
    const r = classifyUndernutrition({ waz: 0.99, haz: -1.77, whz: 2.56 });
    expect(r.current_undernutrition_conditions).toEqual([]);
    expect(r.label).toBe("No undernutrition detected");
    expect(r.label).not.toMatch(/normal|overweight|obes/i);
  });

  it("CASE 2: WAZ -2.4 -> Underweight", () => {
    const r = classifyUndernutrition({ waz: -2.4, haz: -1.0, whz: -0.5 });
    expect(r.current_undernutrition_conditions).toEqual(["Underweight"]);
    expect(r.label).toBe("Underweight");
  });

  it("CASE 3: HAZ -2.3 -> Stunting", () => {
    const r = classifyUndernutrition({ waz: -1.0, haz: -2.3, whz: -0.8 });
    expect(r.current_undernutrition_conditions).toEqual(["Stunting"]);
    expect(r.label).toBe("Stunting");
  });

  it("CASE 4: WHZ -2.5 -> Wasting (MAM)", () => {
    const r = classifyUndernutrition({ waz: -0.7, haz: -1.1, whz: -2.5 });
    expect(r.current_undernutrition_conditions).toEqual(["Wasting"]);
    expect(r.wastingCategory).toBe("MAM");
    expect(r.label).toBe("Wasting (MAM)");
  });

  it("WHZ -3.2 -> Wasting (SAM)", () => {
    const r = classifyUndernutrition({ waz: -0.7, haz: -1.1, whz: -3.2 });
    expect(r.current_undernutrition_conditions).toEqual(["Wasting"]);
    expect(r.wastingCategory).toBe("SAM");
    expect(r.label).toBe("Wasting (SAM)");
  });

  it("CASE 5: WAZ -2.5 and HAZ -2.4 -> Underweight + Stunting", () => {
    const r = classifyUndernutrition({ waz: -2.5, haz: -2.4, whz: -1.0 });
    expect(r.current_undernutrition_conditions).toEqual(["Underweight", "Stunting"]);
    expect(r.label).toBe("Underweight + Stunting");
  });

  it("CASE 6: all three low -> Underweight + Stunting + Wasting", () => {
    const r = classifyUndernutrition({ waz: -2.5, haz: -2.4, whz: -2.3 });
    expect(r.current_undernutrition_conditions).toEqual(["Underweight", "Stunting", "Wasting"]);
    expect(r.label).toBe("Underweight + Stunting + Wasting (MAM)");
    expect(r.wastingCategory).toBe("MAM");
  });

  it("other two-condition overlaps keep the fixed order and name MAM/SAM", () => {
    expect(classifyUndernutrition({ waz: -2.1, haz: -1.0, whz: -2.1 }).label).toBe("Underweight + Wasting (MAM)");
    expect(classifyUndernutrition({ waz: -1.0, haz: -2.1, whz: -2.1 }).label).toBe("Stunting + Wasting (MAM)");
    expect(classifyUndernutrition({ waz: -2.1, haz: -2.1, whz: -3.4 }).label).toBe("Underweight + Stunting + Wasting (SAM)");
  });

  it("boundary: convention is strict < -2, so exactly -2 is not flagged", () => {
    expect(UNDERNUTRITION_Z_CUTOFF).toBe(-2);
    const atCutoff = classifyUndernutrition({ waz: -2, haz: -2, whz: -2 });
    expect(atCutoff.current_undernutrition_conditions).toEqual([]);
    expect(atCutoff.wastingCategory).toBeNull();
    expect(atCutoff.label).toBe(NO_UNDERNUTRITION_LABEL);
    const justBelow = classifyUndernutrition({ waz: -2.001, haz: -2.001, whz: -2.001 });
    expect(justBelow.current_undernutrition_conditions).toEqual(["Underweight", "Stunting", "Wasting"]);
    expect(justBelow.wastingCategory).toBe("MAM");
    expect(justBelow.label).toBe("Underweight + Stunting + Wasting (MAM)");
    const atSamCutoff = classifyUndernutrition({ waz: 0, haz: 0, whz: -3 });
    expect(atSamCutoff.label).toBe("Wasting (MAM)");
    const justBelowSam = classifyUndernutrition({ waz: 0, haz: 0, whz: -3.001 });
    expect(justBelowSam.label).toBe("Wasting (SAM)");
    const justAbove = classifyUndernutrition({ waz: -1.999, haz: -1.999, whz: -1.999 });
    expect(justAbove.current_undernutrition_conditions).toEqual([]);
  });

  it("high positive z-scores never classify (no overweight / obesity in scope)", () => {
    const r = classifyUndernutrition({ waz: 3.5, haz: 2.5, whz: 4.0 });
    expect(r.current_undernutrition_conditions).toEqual([]);
    expect(r.label).toBe(NO_UNDERNUTRITION_LABEL);
  });

  it("missing indicators are skipped rather than classified", () => {
    expect(classifyUndernutrition({ waz: null, haz: -2.5, whz: null }).label).toBe("Stunting");
    expect(classifyUndernutrition({ waz: null, haz: null, whz: null }).label).toBe(NO_UNDERNUTRITION_LABEL);
  });
});

describe("assessWhoUndernutrition (measurements -> z-scores -> label)", () => {
  it("reports z-scores unclamped alongside the label", () => {
    // Girl, 24 months, 13 kg, 80 cm: WAZ ~ +0.99, HAZ ~ -1.77, WHZ ~ +2.56
    const r = assessWhoUndernutrition({ ageMonths: 24, sex: "female", weightKg: 13, heightCm: 80 })!;
    expect(r.zScores.waz).toBeCloseTo(0.99, 1);
    expect(r.zScores.haz).toBeCloseTo(-1.77, 1);
    expect(r.zScores.whz).toBeCloseTo(2.56, 1);
    expect(r.label).toBe(NO_UNDERNUTRITION_LABEL);
  });

  it("girl 24 months 11.8 kg 78 cm -> Stunting", () => {
    const r = assessWhoUndernutrition({ ageMonths: 24, sex: "female", weightKg: 11.8, heightCm: 78 })!;
    expect(r.current_undernutrition_conditions).toEqual(["Stunting"]);
  });

  it("z-score engine matches WHO published median and -2 SD points", () => {
    expect(whoZScores({ ageMonths: 24, sex: "female", weightKg: 11.4775, heightCm: null }).waz).toBeCloseTo(0, 3);
    expect(whoZScores({ ageMonths: 24, sex: "female", weightKg: 9.0, heightCm: null }).waz).toBeCloseTo(-2, 1);
    expect(whoZScores({ ageMonths: 60, sex: "male", weightKg: null, heightCm: 100.7 }).haz).toBeCloseTo(-2, 1);
    expect(whoZScores({ ageMonths: 30, sex: "female", weightKg: 8.6, heightCm: 80 }).whz).toBeCloseTo(-2, 1);
  });

  it("returns null outside the under-five standards", () => {
    expect(assessWhoUndernutrition({ ageMonths: 70, sex: "male", weightKg: 20, heightCm: 110 })).toBeNull();
    expect(assessWhoUndernutrition({ ageMonths: 24, sex: "", weightKg: 12, heightCm: 85 })).toBeNull();
  });
});
