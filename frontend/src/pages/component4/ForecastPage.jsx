import { useMemo } from 'react';
import {
  Area,
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
import SelectionBar from '../../components/component4/SelectionBar';
import ActiveForecastBar from '../../components/component4/ActiveForecastBar';
import AsyncBoundary from '../../components/component4/AsyncBoundary';
import ForecastCard from '../../components/component4/ForecastCard';
import { Card, Pill } from '../../components/component4/ui';
import useC4Data from '../../components/component4/useC4Data';
import { useComponent4Selection } from '../../context/Component4SelectionContext';
import { getForecastBySelectedMonth } from '../../services/component4/forecastApi';
import {
  formatCases,
  formatNumber,
  priorityBadgeClass,
} from '../../components/component4/utils';
import {
  axisTick,
  chartTooltipStyle,
  HORIZON_KEYS,
  HORIZON_META,
  isPresent,
  targetLabel,
  targetShort,
} from '../../components/component4/format';

function ForecastTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-primary">{label}</p>
      <p className="text-slate-700">
        Predicted cases: <strong>{formatCases(row.predicted)}</strong>
      </p>
      {isPresent(row.lower) && isPresent(row.upper) && (
        <p className="text-slate-700">
          95% interval: {formatCases(row.lower)} - {formatCases(row.upper)}
        </p>
      )}
    </div>
  );
}

export default function ForecastPage() {
  const { district, year, month, selection } = useComponent4Selection();

  const { data, loading, error, reload } = useC4Data(
    () => getForecastBySelectedMonth(selection),
    [district, year, month]
  );

  const chartData = useMemo(() => {
    const forecasts = data?.forecasts;
    if (!forecasts) return [];
    return HORIZON_KEYS.filter((key) => forecasts[key]).map((key) => {
      const f = forecasts[key];
      const hasBand = isPresent(f.lower_95) && isPresent(f.upper_95);
      return {
        name: `${HORIZON_META[key].label} (${targetShort(f.target_date)})`,
        predicted: f.predicted_cases,
        lower: hasBand ? f.lower_95 : null,
        upper: hasBand ? f.upper_95 : null,
        band: hasBand ? [f.lower_95, f.upper_95] : null,
      };
    });
  }, [data]);

  const hasBands = chartData.some((row) => row.band);
  const rows = HORIZON_KEYS.filter((key) => data?.forecasts?.[key]);

  return (
    <div className="min-h-screen">
      <Navbar
        title="Forecast"
        subtitle="Automatic H1, H3 and H6 malnutrition burden forecasts."
      />

      <div className="space-y-5 p-4 md:p-6">
        <SelectionBar />

        <AsyncBoundary
          loading={loading}
          error={error}
          data={data}
          onRetry={reload}
          isEmpty={!rows.length}
          loadingMessage="Loading forecast..."
          emptyTitle="No forecast for this selection"
          emptyMessage="The backend has no forecast for the selected district, year and month."
        >
          <div className="space-y-5">
            <ActiveForecastBar forecast={data} />

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {rows.map((key) => (
                <ForecastCard
                  key={key}
                  title={`${HORIZON_META[key].label} - ${HORIZON_META[key].long}`}
                  data={data.forecasts[key]}
                  accent={HORIZON_META[key].color}
                />
              ))}
            </div>

            <Card
              title="Predicted cases across horizons"
              subtitle={
                hasBands
                  ? 'Line shows predicted cases; shaded area is the 95% prediction interval.'
                  : 'Predicted cases for each forecast horizon.'
              }
            >
              <div style={{ width: '100%', height: 340 }}>
                <ResponsiveContainer>
                  <ComposedChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" />
                    <XAxis dataKey="name" tick={axisTick} />
                    <YAxis tick={axisTick} domain={['auto', 'auto']} />
                    <Tooltip content={<ForecastTooltip />} contentStyle={chartTooltipStyle} />
                    <Legend wrapperStyle={{ fontSize: 14 }} />
                    {hasBands && (
                      <Area
                        type="monotone"
                        dataKey="band"
                        name="95% interval"
                        stroke="none"
                        fill="#6C5CE7"
                        fillOpacity={0.15}
                        connectNulls
                      />
                    )}
                    {hasBands && (
                      <Line
                        type="monotone"
                        dataKey="upper"
                        name="Upper 95%"
                        stroke="#E74C3C"
                        strokeWidth={1.5}
                        strokeDasharray="4 4"
                        dot={{ r: 3 }}
                        connectNulls
                      />
                    )}
                    <Line
                      type="monotone"
                      dataKey="predicted"
                      name="Predicted cases"
                      stroke="#6C5CE7"
                      strokeWidth={3}
                      dot={{ r: 5, fill: '#6C5CE7' }}
                      connectNulls
                    />
                    {hasBands && (
                      <Line
                        type="monotone"
                        dataKey="lower"
                        name="Lower 95%"
                        stroke="#27AE60"
                        strokeWidth={1.5}
                        strokeDasharray="4 4"
                        dot={{ r: 3 }}
                        connectNulls
                      />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card title="Horizon details" subtitle="Values returned by the backend for each horizon">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px] text-base">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-sm text-slate-500">
                      <th className="pb-2 pr-3 font-semibold">Horizon</th>
                      <th className="pb-2 pr-3 font-semibold">Target month</th>
                      <th className="pb-2 pr-3 font-semibold">Predicted cases</th>
                      <th className="pb-2 pr-3 font-semibold">95% interval</th>
                      <th className="pb-2 pr-3 font-semibold">Priority</th>
                      <th className="pb-2 pr-3 font-semibold">Rank</th>
                      <th className="pb-2 pr-3 font-semibold">DMBI</th>
                      <th className="pb-2 pr-3 font-semibold">Triposha</th>
                      <th className="pb-2 pr-3 font-semibold">Uncertainty</th>
                      <th className="pb-2 font-semibold">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((key) => {
                      const f = data.forecasts[key];
                      return (
                        <tr key={key} className="border-b border-slate-50 align-top">
                          <td className="py-3 pr-3 font-bold" style={{ color: HORIZON_META[key].color }}>
                            {HORIZON_META[key].label}
                          </td>
                          <td className="py-3 pr-3">{targetLabel(f.target_date)}</td>
                          <td className="py-3 pr-3 font-semibold text-primary">
                            {formatCases(f.predicted_cases)}
                          </td>
                          <td className="py-3 pr-3">
                            {isPresent(f.lower_95) && isPresent(f.upper_95)
                              ? `${formatCases(f.lower_95)} - ${formatCases(f.upper_95)}`
                              : '-'}
                          </td>
                          <td className="py-3 pr-3">
                            {f.priority_level ? (
                              <Pill className={priorityBadgeClass(f.priority_level)}>
                                {f.priority_level}
                              </Pill>
                            ) : (
                              '-'
                            )}
                          </td>
                          <td className="py-3 pr-3">
                            {isPresent(f.priority_rank) ? `#${f.priority_rank}` : '-'}
                          </td>
                          <td className="py-3 pr-3">{formatNumber(f.dmbi_score, 1)}</td>
                          <td className="py-3 pr-3">
                            {formatNumber(f.triposha_packets)}
                            {isPresent(f.triposha_lower_95) && isPresent(f.triposha_upper_95) && (
                              <span className="block text-sm text-slate-500">
                                {formatNumber(f.triposha_lower_95)} -{' '}
                                {formatNumber(f.triposha_upper_95)}
                              </span>
                            )}
                          </td>
                          <td className="py-3 pr-3">{f.uncertainty_level || '-'}</td>
                          <td className="py-3">{f.confidence_label || '-'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </AsyncBoundary>
      </div>
    </div>
  );
}
