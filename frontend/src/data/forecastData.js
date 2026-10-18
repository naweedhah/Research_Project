import { districts } from './districtData';
import {
  getHorizonMonthTabs,
  getMonthFactor,
  getTrendLabel,
  isAllDistricts,
  riskFromPredictedCases,
  toForecastDistrictScope,
  uncertaintyFromCiWidth,
  addMonths,
  DISTRICT_ALL,
} from '../utils/forecastContextUtils';

const baseHistorical = [
  { year: 2019, historical: 6200 },
  { year: 2020, historical: 6550 },
  { year: 2021, historical: 7100 },
  { year: 2022, historical: 7600 },
  { year: 2023, historical: 8050 },
];

const modelMultipliers = {
  NGBoost: 1,
  XGBoost: 0.98,
  'Random Forest': 0.96,
  LSTM: 1.03,
};

export const modelPerformance = {
  NGBoost: { accuracy: 95.1, rmse: 104, mae: 78 },
  XGBoost: { accuracy: 94.2, rmse: 118, mae: 86 },
  'Random Forest': { accuracy: 91.8, rmse: 142, mae: 104 },
  LSTM: { accuracy: 92.5, rmse: 131, mae: 97 },
};

export const annualTrendData = [
  { year: 2019, total: 6200, mam: 5100, sam: 1100 },
  { year: 2020, total: 6550, mam: 5350, sam: 1200 },
  { year: 2021, total: 7100, mam: 5750, sam: 1350 },
  { year: 2022, total: 7600, mam: 6150, sam: 1450 },
  { year: 2023, total: 8050, mam: 6500, sam: 1550 },
];

export const riskDistribution = [
  { name: 'Very High', value: 3, color: '#E74C3C' },
  { name: 'High', value: 5, color: '#F97316' },
  { name: 'Medium', value: 7, color: '#F39C12' },
  { name: 'Low', value: 6, color: '#27AE60' },
  { name: 'Very Low', value: 4, color: '#3498DB' },
];

function hashString(value) {
  return String(value)
    .split('')
    .reduce((sum, char) => sum + char.charCodeAt(0), 0);
}

function riskFromCases(cases) {
  return riskFromPredictedCases(cases, true);
}

function buildDistrictMonthForecast(base, monthOffset, modelMult, monthFactor) {
  const seed = hashString(base.name);
  const growth = ((seed % 9) - 3) * 4 + monthOffset * (6 + (seed % 5));
  const predicted = Math.max(
    70,
    Math.round((base.cases * 1.18 + growth) * modelMult * monthFactor)
  );
  // Highlight Nuwara Eliya to match demo screenshot when near Jan 2027
  let adjusted = predicted;
  if (base.name === 'Nuwara Eliya') {
    adjusted = Math.round((620 + monthOffset * 18) * modelMult * (monthFactor / 0.95));
  } else if (base.name === 'Galle') {
    adjusted = Math.round((98 + monthOffset * 4) * modelMult);
  } else if (base.name === 'Badulla') {
    adjusted = Math.round((540 + monthOffset * 12) * modelMult);
  } else if (base.name === 'Batticaloa') {
    adjusted = Math.round((510 + monthOffset * 10) * modelMult);
  }

  const ciRatio = 0.08 + ((seed + monthOffset * 3) % 12) / 100;
  const half = Math.max(12, Math.round(adjusted * ciRatio));
  const lower = Math.max(0, adjusted - half);
  const upper = adjusted + half;
  const uncertainty = uncertaintyFromCiWidth(upper - lower, adjusted);

  return {
    name: base.name,
    id: base.id,
    predictedCases: adjusted,
    lower,
    upper,
    ci: `${lower.toLocaleString()} – ${upper.toLocaleString()}`,
    risk: riskFromPredictedCases(adjusted, false),
    uncertainty,
    actual: Math.round(base.cases * 0.92),
  };
}

function summarizeMonth(districtRows) {
  const total = districtRows.reduce((sum, d) => sum + d.predictedCases, 0);
  const avgPredictedCases = Math.round(total / districtRows.length);
  const sorted = [...districtRows].sort((a, b) => b.predictedCases - a.predictedCases);
  const highest = sorted[0];
  const lowest = sorted[sorted.length - 1];
  const avgWidth = Math.round(
    districtRows.reduce((sum, d) => sum + (d.upper - d.lower), 0) / districtRows.length
  );
  const avgLower = Math.round(avgPredictedCases - avgWidth / 2);
  const avgUpper = Math.round(avgPredictedCases + avgWidth / 2);

  return {
    avgPredictedCases,
    highestDistrict: highest.name,
    highestCases: highest.predictedCases,
    lowestDistrict: lowest.name,
    lowestCases: lowest.predictedCases,
    avgUncertaintyWidth: avgWidth,
    avgUncertaintyLevel: uncertaintyFromCiWidth(avgWidth, avgPredictedCases),
    avgLower,
    avgUpper,
    avgCi: `${avgLower.toLocaleString()} – ${avgUpper.toLocaleString()}`,
    avgRisk: riskFromPredictedCases(avgPredictedCases, false),
    national: {
      name: DISTRICT_ALL,
      predictedCases: total,
      lower: Math.round(total * 0.94),
      upper: Math.round(total * 1.06),
      ci: `${Math.round(total * 0.94).toLocaleString()} – ${Math.round(total * 1.06).toLocaleString()}`,
      risk: riskFromPredictedCases(total, true),
      uncertainty: 'Medium',
    },
    top5: sorted.slice(0, 5),
  };
}

/**
 * Monthly horizon forecast used by the redesigned Forecast page.
 * Keeps district/month values deterministic so other pages stay in sync.
 */
export function generateMonthlyForecast({
  model = 'NGBoost',
  district = DISTRICT_ALL,
  horizon = 1,
  startMonth = 'January',
  startYear = 2027,
}) {
  const mult = modelMultipliers[model] || 1;
  const tabs = getHorizonMonthTabs(startMonth, startYear, horizon);
  const monthsData = {};
  const districtTrendMap = {};

  tabs.forEach((tab) => {
    const monthFactor = getMonthFactor(tab.month);
    const districtRows = districts.map((d) => {
      const row = buildDistrictMonthForecast(d, tab.index, mult, monthFactor);
      if (!districtTrendMap[d.name]) districtTrendMap[d.name] = [];
      districtTrendMap[d.name].push(row.predictedCases);
      return row;
    });

    districtRows.forEach((row) => {
      row.trend = getTrendLabel(districtTrendMap[row.name]);
    });

    const summary = summarizeMonth(districtRows);
    monthsData[tab.label] = {
      month: tab.month,
      year: tab.year,
      label: tab.label,
      districts: districtRows,
      summary,
      national: summary.national,
      top5: summary.top5,
    };
  });

  // Attach horizon trend per district
  Object.values(monthsData).forEach((snap) => {
    snap.districts = snap.districts.map((row) => ({
      ...row,
      trend: getTrendLabel(districtTrendMap[row.name]),
      series: tabs.map((tab, idx) => ({
        label: tab.shortLabel,
        month: tab.month,
        year: tab.year,
        key: tab.label,
        predicted: districtTrendMap[row.name][idx],
      })),
    }));
  });

  const table = districts.map((base) => {
    const cells = {};
    tabs.forEach((tab) => {
      const row = monthsData[tab.label].districts.find((d) => d.name === base.name);
      cells[tab.label] = row;
    });
    const first = cells[tabs[0].label];
    return {
      district: base.name,
      id: base.id,
      actual: first?.actual ?? Math.round(base.cases * 0.92),
      actualLabel: (() => {
        const prev = addMonths(startMonth, startYear, -1);
        return `${prev.month.slice(0, 3)} ${prev.year} (Actual)`;
      })(),
      cells,
    };
  });

  // Chart series: for selected scope — monthly points across horizon (+ optional prior actual)
  const firstTab = tabs[0];
  const prev = addMonths(startMonth, startYear, -1);
  const scopeDistrict = isAllDistricts(district) ? null : district;

  const series = [
    {
      year: `${prev.month.slice(0, 3)} ${prev.year}`,
      label: `${prev.month.slice(0, 3)} ${prev.year}`,
      historical: scopeDistrict
        ? Math.round((districts.find((d) => d.name === scopeDistrict)?.cases || 400) * 0.92)
        : Math.round(districts.reduce((s, d) => s + d.cases, 0) * 0.92),
      predicted: null,
      upper: null,
      lower: null,
    },
    ...tabs.map((tab) => {
      const snap = monthsData[tab.label];
      if (scopeDistrict) {
        const row = snap.districts.find((d) => d.name === scopeDistrict);
        return {
          year: tab.shortLabel,
          label: tab.label,
          historical: null,
          predicted: row.predictedCases,
          upper: row.upper,
          lower: row.lower,
        };
      }
      return {
        year: tab.shortLabel,
        label: tab.label,
        historical: null,
        predicted: snap.national.predictedCases,
        upper: snap.national.upper,
        lower: snap.national.lower,
      };
    }),
  ];

  const activeKey = firstTab.label;
  const activeSnap = monthsData[activeKey];

  return {
    kind: 'monthly',
    series,
    table,
    months: tabs,
    monthsData,
    performance: modelPerformance[model] || modelPerformance.NGBoost,
    model,
    district: isAllDistricts(district) ? DISTRICT_ALL : district,
    horizon: Number(horizon),
    startMonth,
    startYear,
    activeMonth: firstTab.month,
    activeYear: firstTab.year,
    until: tabs[tabs.length - 1].year,
    year: firstTab.year,
    month: firstTab.month,
    summary: activeSnap.summary,
  };
}

/** Legacy annual generator — kept for older consumers / District Details fallbacks. */
export function generateForecast({
  model = 'NGBoost',
  district = 'National',
  until = 2035,
  year,
  month = 'January',
  horizon = 1,
  startMonth,
  startYear,
}) {
  // Prefer monthly generator when start month/year provided
  if (startMonth && startYear) {
    return generateMonthlyForecast({
      model,
      district: isAllDistricts(district) ? DISTRICT_ALL : district,
      horizon,
      startMonth,
      startYear,
    });
  }

  const mult = modelMultipliers[model] || 1;
  const monthFactor = getMonthFactor(month);
  const scope = toForecastDistrictScope(district);
  const isNational = isAllDistricts(district) || scope === 'National';
  const districtFactor = isNational ? 1 : 0.06 + (scope.length % 7) * 0.01;

  const start = isNational ? 8180 : 480;
  const growth = isNational ? 240 : 18;
  const horizonYear = year && year >= 2024 ? year : until;

  const series = baseHistorical.map((row) => ({
    year: row.year,
    historical: Math.round(
      row.historical * districtFactor * monthFactor * (isNational ? 1 : 0.065)
    ),
    predicted: null,
    upper: null,
    lower: null,
  }));

  if (!isNational) {
    series.forEach((row, i) => {
      row.historical = Math.round((420 + i * 15 + scope.length) * monthFactor);
    });
  }

  const lastHist = series[series.length - 1];
  lastHist.predicted = lastHist.historical;
  lastHist.upper = lastHist.historical;
  lastHist.lower = lastHist.historical;

  const table = [];
  for (let forecastYear = 2024; forecastYear <= horizonYear; forecastYear++) {
    const offset = forecastYear - 2023;
    const predicted = Math.round(
      (start + growth * offset) *
        mult *
        monthFactor *
        (isNational ? 1 : districtFactor * 10)
    );
    const band = Math.round(predicted * 0.06);
    const row = {
      year: forecastYear,
      historical: null,
      predicted,
      upper: predicted + band,
      lower: Math.max(0, predicted - band),
    };
    series.push(row);
    table.push({
      year: forecastYear,
      month: forecastYear === year ? month : null,
      predictedCases: predicted,
      ci: `${(predicted - band).toLocaleString()} – ${(predicted + band).toLocaleString()}`,
      risk: riskFromCases(isNational ? predicted : predicted * 15),
    });
  }

  return {
    kind: 'annual',
    series,
    table,
    performance: modelPerformance[model] || modelPerformance.NGBoost,
    model,
    district: isNational ? DISTRICT_ALL : scope,
    until: horizonYear,
    year: year || horizonYear,
    month,
    horizon: 1,
  };
}

export function generateDistrictForecast(districtName, until = 2030) {
  const seed = districtName.length * 17;
  const base = 420 + (seed % 100);
  const series = [];
  for (let year = 2019; year <= until; year++) {
    const i = year - 2019;
    if (year <= 2023) {
      const historical = Math.round(base + i * 15);
      series.push({
        year,
        historical,
        predicted: year === 2023 ? historical : null,
        upper: year === 2023 ? historical : null,
        lower: year === 2023 ? historical : null,
      });
    } else {
      const predicted = Math.round(base + (year - 2019) * 16 + (seed % 20));
      const band = Math.round(predicted * 0.08);
      series.push({
        year,
        historical: null,
        predicted,
        upper: predicted + band,
        lower: predicted - band,
      });
    }
  }
  return series;
}

export function getMonthSeriesForDistrict(result, districtName) {
  if (!result?.months?.length || !result?.monthsData) return [];
  return result.months.map((tab) => {
    const snap = result.monthsData[tab.label];
    const row = isAllDistricts(districtName)
      ? snap.national
      : snap.districts.find((d) => d.name === districtName);
    return {
      year: tab.shortLabel,
      label: tab.label,
      historical: null,
      predicted: row?.predictedCases ?? null,
      upper: row?.upper ?? null,
      lower: row?.lower ?? null,
    };
  });
}
