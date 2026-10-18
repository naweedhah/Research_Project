import { describe, expect, it } from "vitest";
import { displayPredictedSeverity, formatPercent, formatStatus, malnutritionSeverityApplies } from "./utils";

describe("formatters", () => {
  it("formats risk as a percentage", () => {
    expect(formatPercent(0.59)).toBe("59%");
    expect(formatPercent(0)).toBe("0%");
    expect(formatPercent(0.004)).toBe("<1%");
    expect(formatPercent(0.011)).toBe("1%");
  });
  it("formats status labels", () => {
    expect(formatStatus("moderate_wasting")).toBe("MAM");
    expect(formatStatus("severe_wasting")).toBe("SAM");
    expect(formatStatus("MAM")).toBe("MAM");
    expect(formatStatus("SAM")).toBe("SAM");
  });

  it("does not apply severity when the predicted type is Normal", () => {
    expect(malnutritionSeverityApplies("Normal")).toBe(false);
    expect(malnutritionSeverityApplies("normal")).toBe(false);
    expect(malnutritionSeverityApplies("")).toBe(false);
    expect(malnutritionSeverityApplies(null)).toBe(false);
    expect(malnutritionSeverityApplies("Stunting")).toBe(true);
    expect(malnutritionSeverityApplies("Underweight")).toBe(true);
    expect(malnutritionSeverityApplies("MAM")).toBe(true);
    expect(malnutritionSeverityApplies("SAM")).toBe(true);
  });

  it("hides a formatted severity for Normal and keeps it for other types", () => {
    expect(displayPredictedSeverity("Normal", "Moderate")).toBeNull();
    expect(displayPredictedSeverity("normal", "severe")).toBeNull();
    expect(displayPredictedSeverity("Stunting", "Moderate")).toBe("Moderate");
    expect(displayPredictedSeverity("Underweight", "Severe")).toBe("Severe");
  });
});
