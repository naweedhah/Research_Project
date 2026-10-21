import { describe, expect, it } from "vitest";
import { formatPercent, formatStatus } from "./utils";

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
});
