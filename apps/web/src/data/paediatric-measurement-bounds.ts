/**
 * Age-specific weight and height limits for children 0–60 months.
 * Bounds follow WHO Child Growth Standards biologically implausible flags:
 * weight-for-age z < -6 or > +5, length/height-for-age z < -6 or > +6.
 * Combined-sex ranges so SAM and large-for-age children can still be recorded.
 */
const KNOTS: { age: number; minKg: number; maxKg: number; minCm: number; maxCm: number }[] = [
  { age: 0, minKg: 1.4, maxKg: 6.2, minCm: 38, maxCm: 62 },
  { age: 1, minKg: 2.0, maxKg: 7.8, minCm: 43, maxCm: 68 },
  { age: 2, minKg: 2.5, maxKg: 9.0, minCm: 47, maxCm: 72 },
  { age: 3, minKg: 2.9, maxKg: 10.0, minCm: 50, maxCm: 76 },
  { age: 4, minKg: 3.2, maxKg: 10.8, minCm: 52, maxCm: 78 },
  { age: 5, minKg: 3.5, maxKg: 11.5, minCm: 54, maxCm: 80 },
  { age: 6, minKg: 3.7, maxKg: 12.2, minCm: 55, maxCm: 83 },
  { age: 9, minKg: 4.3, maxKg: 14.0, minCm: 59, maxCm: 88 },
  { age: 12, minKg: 4.9, maxKg: 15.6, minCm: 62, maxCm: 93 },
  { age: 15, minKg: 5.3, maxKg: 16.9, minCm: 65, maxCm: 97 },
  { age: 18, minKg: 5.7, maxKg: 18.2, minCm: 67, maxCm: 101 },
  { age: 21, minKg: 6.1, maxKg: 19.4, minCm: 69, maxCm: 104 },
  { age: 24, minKg: 6.5, maxKg: 20.6, minCm: 71, maxCm: 107 },
  { age: 30, minKg: 7.2, maxKg: 23.2, minCm: 74, maxCm: 113 },
  { age: 36, minKg: 7.8, maxKg: 25.8, minCm: 77, maxCm: 118 },
  { age: 42, minKg: 8.4, maxKg: 28.2, minCm: 80, maxCm: 123 },
  { age: 48, minKg: 9.0, maxKg: 30.6, minCm: 82, maxCm: 127 },
  { age: 54, minKg: 9.5, maxKg: 33.0, minCm: 84, maxCm: 131 },
  { age: 60, minKg: 10.0, maxKg: 35.0, minCm: 86, maxCm: 135 },
];

const BMI_MIN = 8.5;
const BMI_MAX = 26.0;

export type AgeMeasurementBounds = {
  minKg: number;
  maxKg: number;
  minCm: number;
  maxCm: number;
};

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function boundsForAgeMonths(ageMonths: number): AgeMeasurementBounds {
  const age = Math.min(60, Math.max(0, ageMonths));
  for (let i = 0; i < KNOTS.length - 1; i += 1) {
    const left = KNOTS[i];
    const right = KNOTS[i + 1];
    if (age >= left.age && age <= right.age) {
      const t = right.age === left.age ? 0 : (age - left.age) / (right.age - left.age);
      return {
        minKg: Number(lerp(left.minKg, right.minKg, t).toFixed(1)),
        maxKg: Number(lerp(left.maxKg, right.maxKg, t).toFixed(1)),
        minCm: Number(lerp(left.minCm, right.minCm, t).toFixed(0)),
        maxCm: Number(lerp(left.maxCm, right.maxCm, t).toFixed(0)),
      };
    }
  }
  const last = KNOTS[KNOTS.length - 1];
  return { minKg: last.minKg, maxKg: last.maxKg, minCm: last.minCm, maxCm: last.maxCm };
}

export function unusualMeasurementMessages(ageMonths: number, weightKg: number, heightCm: number): string[] {
  if (!Number.isFinite(ageMonths) || !Number.isFinite(weightKg) || !Number.isFinite(heightCm)) return [];
  const bounds = boundsForAgeMonths(ageMonths);
  const ageLabel = Number.isInteger(ageMonths) ? String(ageMonths) : ageMonths.toFixed(1);
  const issues: string[] = [];
  if (weightKg < bounds.minKg || weightKg > bounds.maxKg) {
    issues.push(
      `Weight ${weightKg} kg is not realistic for a child aged ${ageLabel} months. Expected about ${bounds.minKg}–${bounds.maxKg} kg at this age.`,
    );
  }
  if (heightCm < bounds.minCm || heightCm > bounds.maxCm) {
    issues.push(
      `Height ${heightCm} cm is not realistic for a child aged ${ageLabel} months. Expected about ${bounds.minCm}–${bounds.maxCm} cm at this age.`,
    );
  }
  if (heightCm >= 40) {
    const bmi = weightKg / (heightCm / 100) ** 2;
    if (Number.isFinite(bmi) && (bmi < BMI_MIN || bmi > BMI_MAX)) {
      issues.push(
        `Weight ${weightKg} kg with height ${heightCm} cm does not match a realistic body size for this age. Check that weight is in kilograms and height is in centimetres.`,
      );
    }
  }
  return issues;
}
