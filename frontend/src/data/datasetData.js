import { districts } from './districtData';

export const datasetRows = districts.flatMap((d) =>
  [2019, 2020, 2021, 2022, 2023].map((year, i) => ({
    id: `${d.id}-${year}`,
    district: d.name,
    year,
    childrenPopulation: d.childPopulation - (4 - i) * 800,
    malnutritionCases: Math.max(80, Math.round(d.cases * (0.75 + i * 0.06))),
    riskLevel: d.risk,
    climateFactor: d.rainfallVariation + (i % 3),
    economicFactor: d.povertyRate + (i % 2),
  }))
);
