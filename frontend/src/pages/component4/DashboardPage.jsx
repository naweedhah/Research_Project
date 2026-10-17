import { Link } from 'react-router-dom';
import { Activity, BellRing, Baby, Gauge, Package, ShieldAlert } from 'lucide-react';
import Navbar from '../../components/layout/Navbar';
import ActiveForecastBar from '../../components/component4/ActiveForecastBar';
import SelectionRequiredNotice from '../../components/component4/SelectionRequiredNotice';
import AsyncBoundary from '../../components/component4/AsyncBoundary';
import ForecastCard from '../../components/component4/ForecastCard';
import PriorityMap from '../../components/component4/PriorityMap';
import { Card, MetricTile, Pill, Stat } from '../../components/component4/ui';
import useC4Data, { useBoundaries } from '../../components/component4/useC4Data';
import { useComponent4Selection } from '../../context/Component4SelectionContext';
import { getDashboardSummaryBySelectedMonth } from '../../services/component4/dashboardApi';
import { getWarningSummary } from '../../services/component4/warningApi';
import { formatCases, formatNumber } from '../../components/component4/utils';
import {
  HORIZON_KEYS,
  HORIZON_META,
  directionBadgeClass,
  formatPercent,
  isPresent,
  severityBadgeClass,
  targetLabel,
} from '../../components/component4/format';

function TrendCard({ trend }) {
  if (!trend?.trend_summary) return null;
  const t = trend.trend_summary;
  return (
    <Card
      title="Trend direction"
      subtitle="Forecast burden and Triposha demand from H1 to H6"
      action={
        <Link to="/c4/trend-analysis" className="text-base font-semibold text-secondary hover:underline">
          Trend analysis
        </Link>
      }
    >
      <div className="mb-3 flex flex-wrap gap-2">
        {isPresent(t.burden_direction) && (
          <Pill className={directionBadgeClass(t.burden_direction)}>
            Burden: {t.burden_direction}
          </Pill>
        )}
        {isPresent(t.resource_direction) && (
          <Pill className={directionBadgeClass(t.resource_direction)}>
            Triposha demand: {t.resource_direction}
          </Pill>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {isPresent(t.h1_to_h3_change_percent) && (
          <Stat label="Cases H1 to H3" value={formatPercent(t.h1_to_h3_change_percent)} />
        )}
        {isPresent(t.h3_to_h6_change_percent) && (
          <Stat label="Cases H3 to H6" value={formatPercent(t.h3_to_h6_change_percent)} />
        )}
        {isPresent(t.h1_to_h6_change_percent) && (
          <Stat label="Cases H1 to H6" value={formatPercent(t.h1_to_h6_change_percent)} />
        )}
        {isPresent(t.triposha_h1_to_h6_change_percent) && (
          <Stat
            label="Triposha H1 to H6"
            value={formatPercent(t.triposha_h1_to_h6_change_percent)}
          />
        )}
      </div>
      {trend.planning_interpretation && (
        <p className="mt-3 rounded-xl bg-secondary/5 px-3 py-3 text-base text-slate-700">
          {trend.planning_interpretation}
        </p>
      )}
    </Card>
  );
}

function ExplanationCard({ explanations }) {
  const h1 = Array.isArray(explanations)
    ? explanations.find((e) => Number(e.horizon) === 1) || explanations[0]
    : null;
  if (!h1) return null;

  return (
    <Card
      title="Forecast explanation (H1)"
      subtitle="Model contribution summary - not a causal claim"
      action={
        <Link to="/c4/explainable-ai" className="text-base font-semibold text-secondary hover:underline">
          Full explanation
        </Link>
      }
    >
      {h1.dominant_domain && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Pill className="bg-secondary/10 text-secondary">{h1.dominant_domain}</Pill>
          {h1.dominant_domain_direction && (
            <Pill className="bg-slate-100 text-slate-700">
              {h1.dominant_domain_direction}
            </Pill>
          )}
          {isPresent(h1.dominant_domain_shap) && (
            <span className="text-base text-slate-600">
              {formatNumber(h1.dominant_domain_shap, 2)} cases
            </span>
          )}
        </div>
      )}
      {h1.explanation && (
        <p className="line-clamp-6 text-base leading-relaxed text-slate-700">
          {h1.explanation}
        </p>
      )}
    </Card>
  );
}

function WarningsCard({ state }) {
  const summary = state.data;
  return (
    <Card
      title="Current early warnings"
      subtitle="Independent of the selected month"
      action={
        <Link to="/c4/early-warning" className="text-base font-semibold text-secondary hover:underline">
          View all
        </Link>
      }
    >
      {state.loading && !summary && (
        <p className="text-base text-slate-500">Loading warnings...</p>
      )}
      {state.error && (
        <p className="text-base text-danger">
          Unable to load warnings: {state.error.message}
        </p>
      )}
      {summary && (
        <>
          <div className="mb-3 flex flex-wrap gap-2">
            <Pill className="bg-red-100 text-red-800">
              Critical: {summary.critical_count ?? 0}
            </Pill>
            <Pill className="bg-orange-100 text-orange-800">
              High: {summary.high_count ?? 0}
            </Pill>
          </div>
          {(summary.latest_warnings || []).length === 0 ? (
            <p className="text-base text-slate-500">No warnings listed.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {summary.latest_warnings.map((w) => (
                <li key={w.district} className="flex items-start justify-between gap-3 py-2.5">
                  <div>
                    <p className="text-base font-semibold text-primary">{w.district}</p>
                    {w.nearest_warning_month_display && (
                      <p className="text-sm text-slate-500">
                        Nearest: H{w.nearest_warning_horizon} - {w.nearest_warning_month_display}
                      </p>
                    )}
                  </div>
                  <Pill className={severityBadgeClass(w.overall_severity)}>
                    {w.overall_severity}
                  </Pill>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Card>
  );
}

export default function DashboardPage() {
  const { district, year, month, selection, hasSelection } = useComponent4Selection();

  const summaryState = useC4Data(
    () => getDashboardSummaryBySelectedMonth(selection),
    [district, year, month],
    { enabled: hasSelection }
  );
  const warningState = useC4Data(() => getWarningSummary(), []);
  const { boundaries } = useBoundaries();

  const summary = summaryState.data;
  const forecast = summary?.forecast;
  const h1 = forecast?.forecasts?.h1;
  const mapDistricts = summary?.gis?.priority_maps?.h1?.districts;
  const warningSummary = warningState.data;

  return (
    <div className="min-h-screen">
      <Navbar title="Dashboard" subtitle="AI-Powered Childhood Nutrition Intelligence." />

      <div className="space-y-5 p-4 md:p-6">
        {!hasSelection ? (
          <>
            <SelectionRequiredNotice />
            <WarningsCard state={warningState} />
          </>
        ) : (
          <>
            <AsyncBoundary
              loading={summaryState.loading}
              error={summaryState.error}
              data={summary}
              onRetry={summaryState.reload}
              loadingMessage="Loading dashboard summary..."
              emptyTitle="No forecast for this selection"
              emptyMessage="The backend has no forecast for the selected district, year and month."
            >
              <div className="space-y-5">
                <ActiveForecastBar forecast={forecast} />

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
                  <MetricTile
                    label="H1 predicted cases"
                    value={formatCases(h1?.predicted_cases)}
                    hint={h1?.target_date ? targetLabel(h1.target_date) : undefined}
                    icon={Baby}
                    accent="#6C5CE7"
                  />
                  <MetricTile
                    label="H1 priority"
                    value={h1?.priority_level || '-'}
                    hint={isPresent(h1?.priority_rank) ? `Rank #${h1.priority_rank}` : undefined}
                    icon={ShieldAlert}
                    accent="#E74C3C"
                  />
                  <MetricTile
                    label="H1 DMBI score"
                    value={formatNumber(h1?.dmbi_score, 1)}
                    hint={h1?.confidence_label}
                    icon={Gauge}
                    accent="#0B1F4D"
                  />
                  <MetricTile
                    label="H1 Triposha packets"
                    value={formatNumber(h1?.triposha_packets)}
                    hint={
                      isPresent(h1?.triposha_lower_95) && isPresent(h1?.triposha_upper_95)
                        ? `Range ${formatNumber(h1.triposha_lower_95)} - ${formatNumber(
                            h1.triposha_upper_95
                          )}`
                        : undefined
                    }
                    icon={Package}
                    accent="#F39C12"
                  />
                  <MetricTile
                    label="Active warnings"
                    value={
                      warningSummary
                        ? formatNumber(warningSummary.warning_count)
                        : warningState.loading
                          ? '...'
                          : '-'
                    }
                    hint={
                      warningSummary
                        ? `${warningSummary.critical_count ?? 0} critical, ${
                            warningSummary.high_count ?? 0
                          } high`
                        : 'Independent of selected month'
                    }
                    icon={BellRing}
                    accent="#27AE60"
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                  {HORIZON_KEYS.map((key) => (
                    <ForecastCard
                      key={key}
                      title={`${HORIZON_META[key].label} - ${HORIZON_META[key].long}`}
                      data={forecast?.forecasts?.[key]}
                      accent={HORIZON_META[key].color}
                    />
                  ))}
                </div>

                <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                  <ExplanationCard explanations={summary?.explainability?.explanations} />
                  <TrendCard trend={summary?.trend_analysis} />
                </div>
              </div>
            </AsyncBoundary>

            <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
              {mapDistricts?.length > 0 && boundaries && (
                <Card
                  className="xl:col-span-3"
                  title="District priority map (H1)"
                  subtitle="Coloured by backend priority level for the selected month"
                  action={
                    <Link
                      to="/c4/gis-map"
                      className="text-base font-semibold text-secondary hover:underline"
                    >
                      Open full map
                    </Link>
                  }
                >
                  <PriorityMap
                    boundaries={boundaries}
                    districts={mapDistricts}
                    selectedDistrict={district}
                    horizonKey="h1"
                    height={380}
                  />
                </Card>
              )}
              <div
                className={
                  mapDistricts?.length > 0 && boundaries ? 'xl:col-span-2' : 'xl:col-span-5'
                }
              >
                <WarningsCard state={warningState} />
              </div>
            </div>

            {h1 && (
              <p className="flex items-center gap-2 text-base text-slate-500">
                <Activity size={16} />
                Priority and DMBI values are relative forecast-based planning indicators from the
                backend, not clinical diagnoses.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
