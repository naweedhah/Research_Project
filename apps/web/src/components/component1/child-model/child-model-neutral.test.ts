import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { CHILD_MODEL_NEUTRAL } from "./ChildModel";

describe("3D child semantics", () => {
  it("keeps GLB colours by default and only uses risk for emissive intensity", () => {
    expect(CHILD_MODEL_NEUTRAL).toBe(false);
    const src = readFileSync(
      path.join(path.dirname(fileURLToPath(import.meta.url)), "./ChildModel.tsx"),
      "utf8",
    );
    expect(src).toMatch(/applyRiskGlow/);
    expect(src).toMatch(/applyNeutralLook/);
    // No geometry deformation from risk
    expect(src).not.toMatch(/scale\.setScalar\(.*risk/);
  });
});
