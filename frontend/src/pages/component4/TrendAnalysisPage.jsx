import { useMemo } from 'react';
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Info } from 'lucide-react';
import Navbar from '../../components/layout/Navbar';
import AsyncBoundary from '../../components/component4/AsyncBoundary';
import SelectionRequiredNotice from '../../components/component4/SelectionRequiredNotice';
import SelectionSummary from '../../components/component4/SelectionSummary';
import { Card, Pill, Stat } from '../../components/component4/ui';
import useC4Data from '../../components/component4/useC4Data';
import { useComponent4Selection } from '../../context/Component4SelectionContext';
import { getClinicalTrendBySelectedMonth } from '../../services/component4/trendApi';
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
  directionBadgeClass,
  formatPercent,
  isPresent,
  targetLabel,
  targetShort,
} from '../../components/component4/format';

export default function TrendAnalysisPage() {
  const { district, year, month, selection, hasSelection } = useComponent4Selection();

  const { data, loading, error, reload } = useC4Data(
    () => getClinicalTrendBySelectedMonth(selection),
    [district, year, month],
    { enabled: hasSelection }
  );

  const points = data?.forecast_points;
  const keys = HORIZON_KEYS.filter((key) => points?.[key]);
  const summary = data?.trend_summary;

  const chartData = useMemo(
    () =>
      keys.map((key) => ({
        name: `${HORIZON_META[key].label} (${targetShort(points[key].target_date)})`,
        cases: points[key].predicted_cases,
        lower: points[key].lower_95,
        upper: points[key].upper_95,
        triposha: points[key].triposha_packets,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data]
  );

  const hasTriposha = chartData.some((row) => isPresent(row.triposha));
  const hasBounds = chartData.some((row) => isPresent(row.lower) && isPresent(row.upper));

  return (
    <div className="min-h-screen">
      <Navbar
        title="Trend Analysis"
        subtitle="How the forecast changes from H1 to H6."
      />

      <div className="space-y-5 p-4 md:p-6">
        {!hasSelection ? (
          <SelectionRequiredNotice />
        ) : (
        <AsyncBoundary
          loading={loading}
          error={error}
          data={data}
          onRetry={reload}
          isEmpty={!keys.length && !summary}
          loadingMessage="Loading trend analysis..."
          emptyTitle="No trend analysis for this selection"
          emptyMessage="The backend has no trend analysis for the selected district, year and month."
        >
          <div className="space-y-5">
            <SelectionSummary />

            {summary && (
              <Card title="Trend direction" subtitle="Percent change between forecast horizons">
                <div className="mb-4 flex flex-wrap gap-2">
                  {isPresent(summary.burden_direction) && (
                    <Pill className={`text-base ${directionBadgeClass(summary.burden_direction)}`}>
                      Burden: {summary.burden_direction}
                    </Pill>
                  )}
                  {isPresent(summary.resource_direction) && (
                    <Pill className={`text-base ${directionBadgeClass(summary.resource_direction)}`}>
                      Triposha demand: {summary.resource_direction}
                    </Pill>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  {isPresent(summary.h1_to_h3_change_percent) && (
                    <Stat
                      label="Cases H1 to H3"
                      value={formatPercent(summary.h1_to_h3_change_percent, 2)}
                    />
                  )}
                  {isPresent(summary.h3_to_h6_change_percent) && (
                    <Stat
                      label="Cases H3 to H6"
                      value={formatPercent(summary.h3_to_h6_change_percent, 2)}
                    />
                  )}
                  {isPresent(summary.h1_to_h6_change_percent) && (
                    <Stat
                      label="Cases H1 to H6"
                      value={formatPercent(summary.h1_to_h6_change_percent, 2)}
                    />
                  )}
                  {isPresent(summary.triposha_h1_to_h6_change_percent) && (
                    <Stat
                      label="Triposha H1 to H6"
                      value={formatPercent(summary.triposha_h1_to_h6_change_percent, 2)}
                    />
                  )}
                </div>
              </Card>
            )}

            {keys.length > 0 && (
              <div className={`grid grid-cols-1 gap-5 ${hasTriposha ? 'xl:grid-cols-2' : ''}`}>
                <Card
                  title="Predicted cases by horizon"
                  subtitle={hasBounds ? 'With 95% interval bounds' : undefined}
                >
                  <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer>
                      <ComposedChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" />
                        <XAxis dataKey="name" tick={axisTick} />
                        <YAxis tick={axisTick} domain={['auto', 'auto']} />
                        <Tooltip
                          contentStyle={chartTooltipStyle}
                          formatter={(value) => formatCases(value)}
                        />
                        <Legend wrapperStyle={{ fontSize: 14 }} />
                        {hasBounds && (
                          <Line
                            type="monotone"
                            dataKey="upper"
                            name="Upper 95%"
                            stroke="#E74C3C"
                            strokeDasharray="4 4"
                            dot={{ r: 3 }}
                          />
                        )}
                        <Line
                          type="monotone"
                          dataKey="cases"
                          name="Predicted cases"
                          stroke="#6C5CE7"
                          strokeWidth={3}
                          dot={{ r: 5, fill: '#6C5CE7' }}
                        />
                        {hasBounds && (
                          <Line
                            type="monotone"
                            dataKey="lower"
                            name="Lower 95%"
                            stroke="#27AE60"
                            strokeDasharray="4 4"
                            dot={{ r: 3 }}
                          />
                        )}
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                {hasTriposha && (
                  <Card title="Triposha packets by horizon">
                    <div style={{ width: '100%', height: 300 }}>
                      <ResponsiveContainer>
                        <ComposedChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" />
                          <XAxis dataKey="name" tick={axisTick} />
                          <YAxis tick={axisTick} domain={['auto', 'auto']} />
                          <Tooltip
                            contentStyle={chartTooltipStyle}
                            formatter={(value) => formatNumber(value)}
                          />
                          <Legend wrapperStyle={{ fontSize: 14 }} />
                          <Line
                            type="monotone"
                            dataKey="triposha"
                            name="Triposha packets"
                            stroke="#F39C12"
                            strokeWidth={3}
                            dot={{ r: 5, fill: '#F39C12' }}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                )}
              </div>
            )}

            {keys.length > 0 && (
              <Card title="Forecast points">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-base">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-sm text-slate-500">
                        <th className="pb-2 pr-3 font-semibold">Horizon</th>
                        <th className="pb-2 pr-3 font-semibold">Target month</th>
                        <th className="pb-2 pr-3 font-semibold">Predicted cases</th>
                        <th className="pb-2 pr-3 font-semibold">95% interval</th>
                        <th className="pb-2 pr-3 font-semibold">Priority</th>
                        <th className="pb-2 pr-3 font-semibold">DMBI</th>
                        <th className="pb-2 pr-3 font-semibold">Triposha</th>
                        <th className="pb-2 font-semibold">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {keys.map((key) => {
                        const p = points[key];
                        return (
                          <tr key={key} className="border-b border-slate-50">
                            <td className="py-3 pr-3 font-bold" style={{ color: HORIZON_META[key].color }}>
                              {HORIZON_META[key].label}
                            </td>
                            <td className="py-3 pr-3">{targetLabel(p.target_date)}</td>
                            <td className="py-3 pr-3 font-semibold text-primary">
                              {formatCases(p.predicted_cases)}
                            </td>
                            <td className="py-3 pr-3">
                              {isPresent(p.lower_95) && isPresent(p.upper_95)
                                ? `${formatCases(p.lower_95)} - ${formatCases(p.upper_95)}`
                                : '-'}
                            </td>
                            <td className="py-3 pr-3">
                              {p.priority_level ? (
                                <Pill className={priorityBadgeClass(p.priority_level)}>
                                  {p.priority_level}
                                </Pill>
                              ) : (
                                '-'
                              )}
                            </td>
                            <td className="py-3 pr-3">{formatNumber(p.dmbi_score, 1)}</td>
                            <td className="py-3 pr-3">{formatNumber(p.triposha_packets)}</td>
                            <td className="py-3">{p.confidence_label || '-'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            {data?.planning_interpretation && (
              <Card title="Planning interpretation">
                <p className="text-base leading-relaxed text-slate-700">
                  {data.planning_interpretation}
                </p>
              </Card>
            )}

            {data?.interpretation_note && (
              <div className="flex items-start gap-3 rounded-2xl border border-secondary/15 bg-secondary/5 px-4 py-4">
                <Info size={20} className="mt-0.5 shrink-0 text-secondary" />
                <p className="text-base text-slate-700">{data.interpretation_note}</p>
              </div>
            )}
          </div>
        </AsyncBoundary>
        )}
      </div>
    </div>
  );
}
