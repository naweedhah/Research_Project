export const MONTH_ALL = 'All Months';
export const DISTRICT_ALL = 'All Districts';

export const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

export const MONTH_OPTIONS = [MONTH_ALL, ...MONTHS];

export const FORECAST_YEARS = [2024, 2025, 2026, 2027, 2028, 2029, 2030, 2035];

export const FORECAST_HORIZONS = [
  { value: 1, label: '1 Month' },
  { value: 3, label: '3 Months' },
  { value: 6, label: '6 Months' },
];

export const FORECAST_MODELS = ['NGBoost', 'XGBoost', 'Random Forest', 'LSTM'];

export const START_MONTH_OPTIONS = (() => {
  const options = [];
  for (const year of [2026, 2027, 2028]) {
    for (const month of MONTHS) {
      options.push({ label: `${month} ${year}`, month, year });
    }
  }
  return options;
})();

export const RISK_LEVELS = ['Very High', 'High', 'Medium', 'Low', 'Very Low'];

export const defaultForecastContext = {
  year: 2027,
  month: 'January',
  district: DISTRICT_ALL,
  model: 'NGBoost',
  horizon: 1,
  startMonth: 'January',
  startYear: 2027,
  activeMonth: 'January',
  activeYear: 2027,
  predictedCases: null,
  risk: null,
  lower: null,
  upper: null,
  uncertainty: null,
  generatedAt: null,
  generated: false,
  result: null,
};

export function monthYearKey(month, year) {
  return `${month} ${year}`;
}

export function parseMonthYear(label) {
  if (!label || typeof label !== 'string') return null;
  const parts = label.trim().split(/\s+/);
  if (parts.length < 2) return null;
  const year = Number(parts[parts.length - 1]);
  const month = parts.slice(0, -1).join(' ');
  if (!MONTHS.includes(month) || Number.isNaN(year)) return null;
  return { month, year };
}

export function addMonths(month, year, offset) {
  const startIndex = MONTHS.indexOf(month);
  if (startIndex < 0) return { month, year };
  const total = startIndex + offset;
  return {
    month: MONTHS[((total % 12) + 12) % 12],
    year: year + Math.floor(total / 12),
  };
}

export function getHorizonMonthTabs(startMonth, startYear, horizon) {
  const months = [];
  const count = Number(horizon) || 1;
  for (let i = 0; i < count; i += 1) {
    const next = addMonths(startMonth, startYear, i);
    months.push({
      month: next.month,
      year: next.year,
      label: monthYearKey(next.month, next.year),
      shortLabel: next.month.slice(0, 3),
      index: i,
    });
  }
  return months;
}

export function migrateForecastContext(context = {}) {
  let month = context.month;
  if (month === 'Non-Selected' || month === MONTH_ALL) month = context.activeMonth || 'January';

  let district = context.district;
  if (district === 'National (all districts)' || district === 'National') {
    district = DISTRICT_ALL;
  }

  const startMonth = context.startMonth || month || 'January';
  const startYear = Number(context.startYear || context.year || 2027);
  const activeMonth = context.activeMonth || month || startMonth;
  const activeYear = Number(context.activeYear || context.year || startYear);
  const horizon = Number(context.horizon || 1);

  return {
    ...defaultForecastContext,
    ...context,
    month: activeMonth,
    year: activeYear,
    district,
    startMonth,
    startYear,
    activeMonth,
    activeYear,
    horizon: [1, 3, 6].includes(horizon) ? horizon : 1,
    model: context.model || 'NGBoost',
  };
}

export function isAllMonths(month) {
  return !month || month === MONTH_ALL || month === 'Non-Selected';
}

export function isMonthSelected(month) {
  return Boolean(month && !isAllMonths(month) && MONTHS.includes(month));
}

export function getMonthFactor(month) {
  if (!isMonthSelected(month)) return 1;
  const monthIndex = MONTHS.indexOf(month) + 1;
  return monthIndex > 0 ? 0.94 + monthIndex / 100 : 1;
}

export function isAllDistricts(district) {
  return (
    !district ||
    district === DISTRICT_ALL ||
    district === 'National' ||
    district === 'National (all districts)'
  );
}

export function normalizeDistrict(district) {
  if (isAllDistricts(district)) return DISTRICT_ALL;
  return district;
}

function contextSeed(year, month, district) {
  const monthIndex = isMonthSelected(month) ? MONTHS.indexOf(month) + 1 : 0;
  const districtKey = isAllDistricts(district) ? DISTRICT_ALL : district;
  const districtSeed = String(districtKey || '')
    .split('')
    .reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return year * 100 + monthIndex * 13 + districtSeed;
}

export function scaleByContext(value, year, month, district) {
  const seed = contextSeed(year, month, district);
  const factor = 0.82 + (seed % 36) / 100;
  return Math.round(Number(value || 0) * factor);
}

export function riskFromPredictedCases(cases, isNational = false) {
  const value = Number(cases) || 0;
  if (isNational) {
    if (value >= 9000) return 'Very High';
    if (value >= 7800) return 'High';
    if (value >= 6500) return 'Medium';
    if (value >= 5200) return 'Low';
    return 'Very Low';
  }
  if (value >= 580) return 'Very High';
  if (value >= 420) return 'High';
  if (value >= 280) return 'Medium';
  if (value >= 160) return 'Low';
  return 'Very Low';
}

export function uncertaintyFromCiWidth(width, predicted) {
  const ratio = predicted > 0 ? width / predicted : 1;
  if (ratio <= 0.12) return 'Low';
  if (ratio <= 0.22) return 'Medium';
  return 'High';
}

export function riskBadgeClass(risk) {
  if (risk === 'Very High' || risk === 'Critical') return 'bg-danger/10 text-danger';
  if (risk === 'High') return 'bg-orange-100 text-orange-700';
  if (risk === 'Medium') return 'bg-warning/10 text-warning';
  if (risk === 'Low') return 'bg-emerald-100 text-emerald-700';
  return 'bg-sky-100 text-sky-700';
}

export function uncertaintyBadgeClass(level) {
  if (level === 'High') return 'bg-danger/10 text-danger';
  if (level === 'Medium') return 'bg-warning/10 text-warning';
  return 'bg-success/10 text-success';
}

export function adjustDistrictRecord(district, year, month) {
  if (!district) return district;
  const cases = scaleByContext(district.cases, year, month, district.name);
  return {
    ...district,
    cases,
    triposha: scaleByContext(district.triposha, year, month, district.name),
    dmpi: Math.min(99, Math.max(20, scaleByContext(district.dmpi, year, month, district.name))),
    triposhaCoverage: Math.min(
      95,
      Math.max(45, scaleByContext(district.triposhaCoverage, year, month, district.name))
    ),
    risk: riskFromPredictedCases(cases, false),
  };
}

/** Prefer forecast result values so all pages stay consistent. */
export function getActiveMonthKey(context) {
  const ctx = migrateForecastContext(context);
  return monthYearKey(ctx.activeMonth, ctx.activeYear);
}

export function getActiveMonthSnapshot(context) {
  const ctx = migrateForecastContext(context);
  const key = getActiveMonthKey(ctx);
  return ctx.result?.monthsData?.[key] || null;
}

export function getDistrictForecastRow(context, districtName) {
  const snapshot = getActiveMonthSnapshot(context);
  if (!snapshot?.districts?.length) return null;
  if (isAllDistricts(districtName)) {
    return snapshot.national || null;
  }
  return snapshot.districts.find((d) => d.name === districtName) || null;
}

export function getForecastAwareDistricts(baseDistricts, context) {
  const ctx = migrateForecastContext(context);
  if (!ctx.generated) return baseDistricts;

  const snapshot = getActiveMonthSnapshot(ctx);
  if (snapshot?.districts?.length) {
    const byName = Object.fromEntries(snapshot.districts.map((d) => [d.name, d]));
    return baseDistricts.map((base) => {
      const forecast = byName[base.name];
      if (!forecast) return adjustDistrictRecord(base, ctx.activeYear, ctx.activeMonth);
      return {
        ...base,
        cases: forecast.predictedCases,
        risk: forecast.risk,
        lower: forecast.lower,
        upper: forecast.upper,
        uncertainty: forecast.uncertainty,
        ci: forecast.ci,
        triposha: Math.round(forecast.predictedCases * 6.2),
        trend: forecast.trend || base.trend,
      };
    });
  }

  return baseDistricts.map((d) => adjustDistrictRecord(d, ctx.activeYear, ctx.activeMonth));
}

export function getActiveForecastSummary(context) {
  const ctx = migrateForecastContext(context);
  if (!ctx.generated) return null;

  const snapshot = getActiveMonthSnapshot(ctx);
  const row = getDistrictForecastRow(ctx, ctx.district);

  if (row) {
    return {
      ...ctx,
      predictedCases: row.predictedCases,
      risk: row.risk,
      lower: row.lower,
      upper: row.upper,
      uncertainty: row.uncertainty,
      ci: row.ci,
      label: getActiveMonthKey(ctx),
      horizonLabel: `${ctx.horizon}-Month Horizon`,
    };
  }

  if (snapshot?.summary) {
    return {
      ...ctx,
      predictedCases: snapshot.summary.avgPredictedCases,
      risk: snapshot.summary.avgRisk || 'Medium',
      lower: snapshot.summary.avgLower,
      upper: snapshot.summary.avgUpper,
      uncertainty: snapshot.summary.avgUncertaintyLevel || 'Medium',
      ci: snapshot.summary.avgCi,
      label: getActiveMonthKey(ctx),
      horizonLabel: `${ctx.horizon}-Month Horizon`,
    };
  }

  return {
    ...ctx,
    label: getActiveMonthKey(ctx),
    horizonLabel: `${ctx.horizon}-Month Horizon`,
  };
}

export function getContextDistrictName(district) {
  if (isAllDistricts(district)) return null;
  return normalizeDistrict(district);
}

export function filterByContextDistrict(items, districtKey, district) {
  const name = getContextDistrictName(district);
  if (!name) return items;
  return items.filter((item) => item[districtKey] === name);
}

export function getDashboardMetricsFromContext(baseMetrics, year, month, district, context) {
  const summary = context ? getActiveForecastSummary(context) : null;
  if (summary?.predictedCases != null) {
    const isNational = isAllDistricts(district);
    const predictedCases = summary.predictedCases;
    const triposhaRequirement = Math.round(predictedCases * 6.2);
    return {
      ...baseMetrics,
      predictedCases,
      triposhaRequirement,
      predictedCasesChange: Number(
        (((predictedCases - baseMetrics.predictedCases) / baseMetrics.predictedCases) * 100).toFixed(1)
      ),
      highRiskDistricts: isNational
        ? baseMetrics.highRiskDistricts
        : Math.max(1, Math.min(6, Math.round(baseMetrics.highRiskDistricts / 4))),
      earlyWarningAlerts: isNational
        ? baseMetrics.earlyWarningAlerts
        : Math.max(1, Math.min(5, Math.round(baseMetrics.earlyWarningAlerts / 3))),
      totalDistricts: isNational ? baseMetrics.totalDistricts : 1,
    };
  }

  const isNational = isAllDistricts(district);
  const predictedCases = scaleByContext(baseMetrics.predictedCases, year, month, district);
  const triposhaRequirement = scaleByContext(
    baseMetrics.triposhaRequirement,
    year,
    month,
    district
  );

  return {
    ...baseMetrics,
    predictedCases,
    triposhaRequirement,
    predictedCasesChange: Number(
      (((predictedCases - baseMetrics.predictedCases) / baseMetrics.predictedCases) * 100).toFixed(1)
    ),
    highRiskDistricts: isNational
      ? baseMetrics.highRiskDistricts
      : Math.max(1, Math.min(6, Math.round(baseMetrics.highRiskDistricts / 4))),
    earlyWarningAlerts: isNational
      ? baseMetrics.earlyWarningAlerts
      : Math.max(1, Math.min(5, Math.round(baseMetrics.earlyWarningAlerts / 3))),
    totalDistricts: isNational ? baseMetrics.totalDistricts : 1,
  };
}

export function getTriposhaDemandFromContext(baseDemand, year, month, district) {
  const total = baseDemand.reduce((sum, item) => sum + item.value, 0);
  const adjustedTotal = scaleByContext(total, year, month, district);
  const ratio = adjustedTotal / total;
  return baseDemand.map((item) => ({
    ...item,
    value: Math.round(item.value * ratio),
  }));
}

export function getTopDistrictsFromContext(topDistricts, allDistricts, year, month, district, context) {
  const snapshot = context ? getActiveMonthSnapshot(context) : null;
  if (snapshot?.top5?.length) {
    const name = getContextDistrictName(district);
    if (name) {
      const selected = snapshot.districts.find((d) => d.name === name);
      if (selected) {
        return [
          {
            rank: 1,
            district: selected.name,
            cases: selected.predictedCases,
            risk: selected.risk,
          },
        ];
      }
    }
    return snapshot.top5.map((d, i) => ({
      rank: i + 1,
      district: d.name,
      cases: d.predictedCases,
      risk: d.risk,
    }));
  }

  const name = getContextDistrictName(district);
  if (!name) return topDistricts;

  const selected = allDistricts.find((d) => d.name === name);
  if (!selected) return topDistricts;

  const adjusted = adjustDistrictRecord(selected, year, month);
  return [
    {
      rank: 1,
      district: adjusted.name,
      cases: adjusted.cases,
      risk: adjusted.risk,
    },
  ];
}

export function getForecastSummaryFromContext(baseSummary, year, month, district, result) {
  if (result?.series?.length) return result.series;
  return baseSummary.map((row) => {
    if (row.year > year) return { ...row, historical: null, predicted: null, upper: null, lower: null };
    if (row.year === year && row.predicted != null) {
      const predicted = scaleByContext(row.predicted, year, month, district);
      const band = Math.round(predicted * 0.06);
      return {
        ...row,
        predicted,
        upper: predicted + band,
        lower: Math.max(0, predicted - band),
      };
    }
    if (row.historical != null) {
      return {
        ...row,
        historical: scaleByContext(row.historical, year, month, district),
      };
    }
    return row;
  });
}

export function toForecastDistrictScope(district) {
  return isAllDistricts(district) ? 'National' : district;
}

export function getForecastScopeLabel(district) {
  return isAllDistricts(district) ? DISTRICT_ALL : district;
}

export function getNationalShapProfile(year, month) {
  const base = {
    prediction: 8426,
    dmpi: 68,
    confidence: 91.5,
    trend: 'Increasing',
    risk: 'Medium',
    triposhaCoverage: 74,
    features: [
      {
        name: 'Poverty Rate',
        value: 29,
        color: '#6C5CE7',
        interpretation:
          'National household poverty remains the strongest structural driver of childhood malnutrition across districts.',
      },
      {
        name: 'Food Inflation',
        value: 24,
        color: '#0B1F4D',
        interpretation:
          'Rising food prices reduce purchasing power nationwide, affecting dietary diversity for under-five children.',
      },
      {
        name: 'Low Birth Weight',
        value: 17,
        color: '#F39C12',
        interpretation:
          'Elevated low birth weight rates contribute to higher predicted caseloads across multiple provinces.',
      },
      {
        name: 'Triposha Coverage',
        value: 15,
        color: '#27AE60',
        interpretation:
          'National supplement coverage gaps reduce the protective effect of Triposha distribution programmes.',
      },
      {
        name: 'Rainfall Variation',
        value: 14,
        color: '#3498DB',
        interpretation:
          'Climate variability disrupts food production and household income patterns at the national level.',
      },
    ],
  };

  return {
    ...base,
    prediction: scaleByContext(base.prediction, year, month, DISTRICT_ALL),
    dmpi: Math.min(99, scaleByContext(base.dmpi, year, month, DISTRICT_ALL)),
    triposhaCoverage: Math.min(
      95,
      scaleByContext(base.triposhaCoverage, year, month, DISTRICT_ALL)
    ),
  };
}

export function getNationalDistrictProfile(allDistricts, year, month, applyContext = true) {
  const count = allDistricts.length || 1;
  const totals = allDistricts.reduce(
    (acc, d) => ({
      cases: acc.cases + d.cases,
      triposha: acc.triposha + d.triposha,
      childPopulation: acc.childPopulation + d.childPopulation,
      dmpi: acc.dmpi + d.dmpi,
      povertyRate: acc.povertyRate + d.povertyRate,
      foodInflation: acc.foodInflation + d.foodInflation,
      lowBirthWeight: acc.lowBirthWeight + d.lowBirthWeight,
      triposhaCoverage: acc.triposhaCoverage + d.triposhaCoverage,
      rainfallVariation: acc.rainfallVariation + d.rainfallVariation,
    }),
    {
      cases: 0,
      triposha: 0,
      childPopulation: 0,
      dmpi: 0,
      povertyRate: 0,
      foodInflation: 0,
      lowBirthWeight: 0,
      triposhaCoverage: 0,
      rainfallVariation: 0,
    }
  );

  const profile = {
    id: 'all-districts',
    name: DISTRICT_ALL,
    province: 'National',
    lat: 7.8731,
    lng: 80.7718,
    cases: totals.cases,
    triposha: totals.triposha,
    childPopulation: totals.childPopulation,
    dmpi: Math.round(totals.dmpi / count),
    trend: 'Increasing',
    risk: 'Medium',
    povertyRate: Math.round(totals.povertyRate / count),
    foodInflation: Math.round(totals.foodInflation / count),
    lowBirthWeight: Math.round(totals.lowBirthWeight / count),
    triposhaCoverage: Math.round(totals.triposhaCoverage / count),
    rainfallVariation: Math.round(totals.rainfallVariation / count),
  };

  if (!applyContext) return profile;
  return adjustDistrictRecord(profile, year, month);
}

export function isNationalForecastScope(district, generated) {
  return Boolean(generated && isAllDistricts(district));
}

export function getTrendLabel(values = []) {
  if (values.length < 2) return 'Stable';
  const first = values[0];
  const last = values[values.length - 1];
  const delta = last - first;
  const threshold = Math.max(8, first * 0.03);
  if (delta > threshold) return 'Increasing';
  if (delta < -threshold) return 'Decreasing';
  return 'Stable';
}
