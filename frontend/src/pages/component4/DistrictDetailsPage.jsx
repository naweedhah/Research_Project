import { useMemo } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Navbar from '../../components/layout/Navbar';
import AsyncBoundary from '../../components/component4/AsyncBoundary';
import ForecastCard from '../../components/component4/ForecastCard';
import SelectionRequiredNotice from '../../components/component4/SelectionRequiredNotice';
import SelectionSummary from '../../components/component4/SelectionSummary';
import ErrorState from '../../components/common/ErrorState';
import { Card, Stat } from '../../components/component4/ui';
import useC4Data from '../../components/component4/useC4Data';
import { useComponent4Selection } from '../../context/Component4SelectionContext';
import {
  getDistrictDetailsBySelectedMonth,
  getDistrictTrendBySelectedMonth,
} from '../../services/component4/districtApi';
import { formatCases, formatNumber } from '../../components/component4/utils';
import {
  axisTick,
  chartTooltipStyle,
  HORIZON_KEYS,
  HORIZON_META,
  isPresent,
  targetShort,
  yearMonthShort,
} from '../../components/component4/format';

const OBSERVATION_FIELDS = [
  ['malnutrition_cases', 'Malnutrition cases', 0],
  ['under_5_population', 'Under-5 population', 0],
  ['live_birth', 'Live births', 0],
  ['triposha_packets_distributed', 'Triposha packets distributed', 0],
  ['low_birth_weight_cases', 'Low birth weight cases', 0],
  ['poverty_line_rs_monthly', 'Poverty line (Rs / month)', 0],
  ['household_income', 'Household income', 0],
  ['temperature', 'Temperature (\u00B0C)', 1],
  ['precipitation', 'Precipitation', 1],
  ['relative_humidity', 'Relative humidity (%)', 1],
];

async function fetchDistrictBundle(selection) {
  const [detailsResult, trendResult] = await Promise.allSettled([
    getDistrictDetailsBySelectedMonth(selection),
    getDistrictTrendBySelectedMonth(selection),
  ]);

  if (detailsResult.status === 'rejected') throw detailsResult.reason;

  return {
    details: detailsResult.value,
    trend: trendResult.status === 'fulfilled' ? trendResult.value : null,
    trendError: trendResult.status === 'rejected' ? trendResult.reason : null,
  };
}

export default function DistrictDetailsPage() {
  const { district, year, month, selection, hasSelection } = useComponent4Selection();

  const { data, loading, error, reload } = useC4Data(
    () => fetchDistrictBundle(selection),
    [district, year, month],
    { enabled: hasSelection }
  );

  const details = data?.details;
  const trend = data?.trend;
  const outlook = details?.forecast_outlook;
  const outlookKeys = HORIZON_KEYS.filter((key) => outlook?.[key]);
  const latest = details?.latest_known_observation;
  const period = details?.historical_period;

  const annualData = useMemo(
    () =>
      (details?.annual_trend || []).map((row) => ({
        year: String(row.year),
        total: row.total_cases,
        mean: row.mean_monthly_cases,
        observations: row.observations,
      })),
    [details]
  );

  const monthlyData = useMemo(() => {
    const rows = [];
    (trend?.recent_observed_trend || []).forEach((p) => {
      rows.push({
        name: yearMonthShort(p.year, p.month),
        observed: p.malnutrition_cases,
        predicted: null,
      });
    });
    HORIZON_KEYS.forEach((key) => {
      const f = trend?.forecast_points?.[key];
      if (!f) return;
      rows.push({
        name: `${HORIZON_META[key].label} (${targetShort(f.target_date)})`,
        observed: null,
        predicted: f.predicted_cases,
      });
    });
    return rows;
  }, [trend]);

  const observationStats = latest
    ? OBSERVATION_FIELDS.filter(([field]) => isPresent(latest[field]))
    : [];

  return (
    <div className="min-h-screen">
      <Navbar
        title="District Details"
        subtitle="Observed history and forecast outlook for the selected district."
      />

      <div className="space-y-5 p-4 md:p-6">
        {!hasSelection ? (
          <SelectionRequiredNotice />
        ) : (
        <AsyncBoundary
          loading={loading}
          error={error}
          data={details}
          onRetry={reload}
          loadingMessage="Loading district details..."
          emptyTitle="No district details for this selection"
          emptyMessage="The backend has no district details for the selected district, year and month."
        >
          <div className="space-y-5">
            <SelectionSummary />

            <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
              {period && (
                <Card title="Historical period" subtitle="Observations available in the historical record">
                  <div className="grid grid-cols-2 gap-2">
                    {isPresent(period.start_year) && (
                      <Stat label="From" value={period.start_year} />
                    )}
                    {isPresent(period.end_year) && <Stat label="To" value={period.end_year} />}
                    {isPresent(period.observations) && (
                      <Stat label="Monthly observations" value={formatNumber(period.observations)} />
                    )}
                  </div>
                </Card>
              )}

              {latest && observationStats.length > 0 && (
                <Card
                  className="xl:col-span-2"
                  title="Latest known observation"
                  subtitle={`${latest.month_name || ''} ${latest.year || ''}`.trim()}
                >
                  <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                    {observationStats.map(([field, label, decimals]) => (
                      <Stat key={field} label={label} value={formatNumber(latest[field], decimals)} />
                    ))}
                  </div>
                </Card>
              )}
            </div>

            {annualData.length > 0 && (
              <Card
                title="Annual trend"
                subtitle="Observed total cases and mean monthly cases per year"
              >
                <div style={{ width: '100%', height: 320 }}>
                  <ResponsiveContainer>
                    <ComposedChart data={annualData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" />
                      <XAxis dataKey="year" tick={axisTick} />
                      <YAxis yAxisId="total" tick={axisTick} />
                      <YAxis yAxisId="mean" orientation="right" tick={axisTick} />
                      <Tooltip
                        contentStyle={chartTooltipStyle}
                        formatter={(value) => formatNumber(value, 1)}
                      />
                      <Legend wrapperStyle={{ fontSize: 14 }} />
                      <Bar
                        yAxisId="total"
                        dataKey="total"
                        name="Total cases"
                        fill="#6C5CE7"
                        fillOpacity={0.85}
                        radius={[6, 6, 0, 0]}
                      />
                      <Line
                        yAxisId="mean"
                        type="monotone"
                        dataKey="mean"
                        name="Mean monthly cases"
                        stroke="#0B1F4D"
                        strokeWidth={2.5}
                        dot={{ r: 4 }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}

            {outlookKeys.length > 0 && (
              <div>
                <h3 className="mb-3 text-lg font-bold text-primary md:text-xl">Forecast outlook</h3>
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                  {outlookKeys.map((key) => (
                    <ForecastCard
                      key={key}
                      title={`${HORIZON_META[key].label} - ${HORIZON_META[key].long}`}
                      data={outlook[key]}
                      accent={HORIZON_META[key].color}
                    />
                  ))}
                </div>
              </div>
            )}

            {data?.trendError && !trend && (
              <ErrorState
                title="Recent trend unavailable"
                message={data.trendError.message}
                onRetry={reload}
              />
            )}

            {trend && monthlyData.length > 0 && (
              <Card
                title="Recent observed months and forecast points"
                subtitle={`Last ${trend.observed_months_count ?? ''} observed months followed by H1, H3 and H6 forecasts`}
              >
                <div style={{ width: '100%', height: 340 }}>
                  <ResponsiveContainer>
                    <ComposedChart data={monthlyData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" />
                      <XAxis dataKey="name" tick={axisTick} interval={0} angle={-35} textAnchor="end" height={70} />
                      <YAxis tick={axisTick} domain={['auto', 'auto']} />
                      <Tooltip
                        contentStyle={chartTooltipStyle}
                        formatter={(value) => formatCases(value)}
                      />
                      <Legend wrapperStyle={{ fontSize: 14 }} verticalAlign="top" />
                      <Line
                        type="monotone"
                        dataKey="observed"
                        name="Observed cases"
                        stroke="#0B1F4D"
                        strokeWidth={2.5}
                        dot={{ r: 4 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="predicted"
                        name="Forecast (H1 / H3 / H6)"
                        stroke="#6C5CE7"
                        strokeWidth={2.5}
                        strokeDasharray="6 4"
                        dot={{ r: 6, fill: '#6C5CE7' }}
                        connectNulls
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}
          </div>
        </AsyncBoundary>
        )}
      </div>
    </div>
  );
}
