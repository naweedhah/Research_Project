import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Navbar from '../../components/layout/Navbar';
import AsyncBoundary from '../../components/component4/AsyncBoundary';
import SelectionRequiredNotice from '../../components/component4/SelectionRequiredNotice';
import SelectionSummary from '../../components/component4/SelectionSummary';
import { Card, Pill, Stat } from '../../components/component4/ui';
import useC4Data from '../../components/component4/useC4Data';
import { useComponent4Selection } from '../../context/Component4SelectionContext';
import { getResourcesBySelectedMonth } from '../../services/component4/resourceApi';
import {
  formatCases,
  formatNumber,
  priorityBadgeClass,
} from '../../components/component4/utils';
import {
  axisTick,
  HORIZON_KEYS,
  HORIZON_META,
  isPresent,
  targetLabel,
  targetShort,
} from '../../components/component4/format';

function TriposhaTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-primary">{row.name}</p>
      <p className="text-slate-700">
        Required Triposha: <strong>{formatNumber(row.packets)}</strong> packets
      </p>
      {isPresent(row.lower) && isPresent(row.upper) && (
        <p className="text-slate-700">
          95% range: {formatNumber(row.lower)} - {formatNumber(row.upper)}
        </p>
      )}
    </div>
  );
}

function ResourceCard({ keyName, plan }) {
  const meta = HORIZON_META[keyName];
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="text-lg font-bold" style={{ color: meta.color }}>
            {meta.label} - {meta.long}
          </p>
          {plan.target_date && (
            <p className="text-sm text-slate-500">{targetLabel(plan.target_date)}</p>
          )}
        </div>
        {plan.priority_level && (
          <Pill className={priorityBadgeClass(plan.priority_level)}>{plan.priority_level}</Pill>
        )}
      </div>

      {isPresent(plan.triposha_packets) && (
        <div className="mb-4">
          <p className="text-sm text-slate-500">Required Triposha packets</p>
          <p className="text-3xl font-bold text-primary md:text-4xl">
            {formatNumber(plan.triposha_packets)}
          </p>
          {isPresent(plan.triposha_lower_95) && isPresent(plan.triposha_upper_95) && (
            <p className="mt-1 text-sm text-slate-500">
              95% range: {formatNumber(plan.triposha_lower_95)} -{' '}
              {formatNumber(plan.triposha_upper_95)}
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {isPresent(plan.predicted_cases) && (
          <Stat label="Predicted cases" value={formatCases(plan.predicted_cases)} />
        )}
        {isPresent(plan.dmbi_score) && (
          <Stat label="DMBI score" value={formatNumber(plan.dmbi_score, 1)} />
        )}
        {isPresent(plan.uncertainty_level) && (
          <Stat label="Uncertainty" value={plan.uncertainty_level} />
        )}
        {isPresent(plan.confidence_label) && (
          <Stat label="Confidence" value={plan.confidence_label} />
        )}
      </div>
    </div>
  );
}

export default function ResourcePlanningPage() {
  const { district, year, month, selection, hasSelection } = useComponent4Selection();

  const { data, loading, error, reload } = useC4Data(
    () => getResourcesBySelectedMonth(selection),
    [district, year, month],
    { enabled: hasSelection }
  );

  const plan = data?.resource_plan;
  const keys = HORIZON_KEYS.filter((key) => plan?.[key]);

  const chartData = useMemo(
    () =>
      keys.map((key) => {
        const p = plan[key];
        const hasRange = isPresent(p.triposha_lower_95) && isPresent(p.triposha_upper_95);
        return {
          key,
          name: `${HORIZON_META[key].label} (${targetShort(p.target_date)})`,
          packets: p.triposha_packets,
          lower: hasRange ? p.triposha_lower_95 : null,
          upper: hasRange ? p.triposha_upper_95 : null,
          err: hasRange
            ? [
                Math.max(0, p.triposha_packets - p.triposha_lower_95),
                Math.max(0, p.triposha_upper_95 - p.triposha_packets),
              ]
            : null,
        };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data]
  );

  const hasRanges = chartData.some((row) => row.err);

  return (
    <div className="min-h-screen">
      <Navbar
        title="Resource Planning"
        subtitle="Forecast-based Triposha requirements for H1, H3 and H6."
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
          isEmpty={!keys.length}
          loadingMessage="Loading resource plan..."
          emptyTitle="No resource plan for this selection"
          emptyMessage="The backend has no resource plan for the selected district, year and month."
        >
          <div className="space-y-5">
            <SelectionSummary />

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {keys.map((key) => (
                <ResourceCard key={key} keyName={key} plan={plan[key]} />
              ))}
            </div>

            <Card
              title="Required Triposha by horizon"
              subtitle={
                hasRanges
                  ? 'Bars show planned packets; whiskers show the 95% range from the backend.'
                  : 'Planned Triposha packets from the backend.'
              }
            >
              <div style={{ width: '100%', height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={chartData} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" />
                    <XAxis dataKey="name" tick={axisTick} />
                    <YAxis tick={axisTick} />
                    <Tooltip content={<TriposhaTooltip />} />
                    <Bar dataKey="packets" name="Triposha packets" radius={[6, 6, 0, 0]} barSize={64}>
                      {chartData.map((row) => (
                        <Cell key={row.key} fill={HORIZON_META[row.key].color} />
                      ))}
                      {hasRanges && (
                        <ErrorBar dataKey="err" width={6} stroke="#0B1F4D" strokeWidth={1.5} />
                      )}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card title="Resource plan details">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-base">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-sm text-slate-500">
                      <th className="pb-2 pr-3 font-semibold">Horizon</th>
                      <th className="pb-2 pr-3 font-semibold">Target month</th>
                      <th className="pb-2 pr-3 font-semibold">Predicted cases</th>
                      <th className="pb-2 pr-3 font-semibold">Triposha packets</th>
                      <th className="pb-2 pr-3 font-semibold">95% range</th>
                      <th className="pb-2 pr-3 font-semibold">Priority</th>
                      <th className="pb-2 pr-3 font-semibold">DMBI</th>
                      <th className="pb-2 pr-3 font-semibold">Uncertainty</th>
                      <th className="pb-2 font-semibold">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {keys.map((key) => {
                      const p = plan[key];
                      return (
                        <tr key={key} className="border-b border-slate-50">
                          <td className="py-3 pr-3 font-bold" style={{ color: HORIZON_META[key].color }}>
                            {HORIZON_META[key].label}
                          </td>
                          <td className="py-3 pr-3">{targetLabel(p.target_date)}</td>
                          <td className="py-3 pr-3">{formatCases(p.predicted_cases)}</td>
                          <td className="py-3 pr-3 font-semibold text-primary">
                            {formatNumber(p.triposha_packets)}
                          </td>
                          <td className="py-3 pr-3">
                            {isPresent(p.triposha_lower_95) && isPresent(p.triposha_upper_95)
                              ? `${formatNumber(p.triposha_lower_95)} - ${formatNumber(
                                  p.triposha_upper_95
                                )}`
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
                          <td className="py-3 pr-3">{p.uncertainty_level || '-'}</td>
                          <td className="py-3">{p.confidence_label || '-'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-sm text-slate-500">
                Triposha figures are forecast-based planning estimates. Stock on hand and
                procurement gaps are not part of this dataset.
              </p>
            </Card>
          </div>
        </AsyncBoundary>
        )}
      </div>
    </div>
  );
}
