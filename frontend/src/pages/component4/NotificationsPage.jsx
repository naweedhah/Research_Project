import { Fragment, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Mail, Search } from 'lucide-react';
import toast from 'react-hot-toast';
import Navbar from '../../components/layout/Navbar';
import AsyncBoundary from '../../components/component4/AsyncBoundary';
import { Card, MetricTile, Pill } from '../../components/component4/ui';
import useC4Data from '../../components/component4/useC4Data';
import { useApp } from '../../context/AppContext';
import { getWarningSummary, getWarnings, sendWarningReport } from '../../services/component4/warningApi';
import { formatCases, formatNumber, priorityBadgeClass } from '../../components/component4/utils';
import {
  HORIZON_KEYS,
  HORIZON_META,
  isPresent,
  severityBadgeClass,
  targetLabel,
} from '../../components/component4/format';

const SEVERITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2 };

async function fetchWarningBundle() {
  const [warnings, summary] = await Promise.all([getWarnings(), getWarningSummary()]);
  return { warnings, summary };
}

function HorizonMetrics({ horizons }) {
  const keys = HORIZON_KEYS.filter((key) => horizons?.[key]);
  if (!keys.length) {
    return <p className="text-base text-slate-500">No horizon metrics returned.</p>;
  }
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
      {keys.map((key) => {
        const h = horizons[key];
        return (
          <div key={key} className="rounded-xl border border-slate-100 bg-white p-4">
            <div className="mb-2 flex items-start justify-between gap-2">
              <div>
                <p className="text-base font-bold" style={{ color: HORIZON_META[key].color }}>
                  {HORIZON_META[key].label}
                </p>
                <p className="text-sm text-slate-500">
                  {h.target_month_display || targetLabel(h.target_date)}
                </p>
              </div>
              {h.priority && (
                <Pill className={priorityBadgeClass(h.priority)}>{h.priority}</Pill>
              )}
            </div>
            <dl className="space-y-1 text-base">
              {isPresent(h.predicted_cases) && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Predicted cases</dt>
                  <dd className="font-semibold text-primary">{formatCases(h.predicted_cases)}</dd>
                </div>
              )}
              {isPresent(h.dmbi_score) && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">DMBI</dt>
                  <dd className="font-semibold text-primary">{formatNumber(h.dmbi_score, 1)}</dd>
                </div>
              )}
              {isPresent(h.triposha_packets) && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Triposha</dt>
                  <dd className="font-semibold text-primary">{formatNumber(h.triposha_packets)}</dd>
                </div>
              )}
              {isPresent(h.uncertainty_level) && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Uncertainty</dt>
                  <dd className="text-right font-semibold text-primary">{h.uncertainty_level}</dd>
                </div>
              )}
              {isPresent(h.confidence_label) && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Confidence</dt>
                  <dd className="text-right font-semibold text-primary">{h.confidence_label}</dd>
                </div>
              )}
              {isPresent(h.warning_triggered) && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Warning triggered</dt>
                  <dd className="font-semibold text-primary">{h.warning_triggered ? 'Yes' : 'No'}</dd>
                </div>
              )}
            </dl>
          </div>
        );
      })}
    </div>
  );
}

export default function NotificationsPage() {
  const { refreshWarnings } = useApp();
  const [severity, setSeverity] = useState('ALL');
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState(null);
  const [sending, setSending] = useState(false);

  // Warnings use the current warning cycle from the backend, never the doctor's
  // selected district / year / month.
  const { data, loading, error, reload } = useC4Data(fetchWarningBundle, []);

  const warnings = useMemo(
    () => (Array.isArray(data?.warnings?.warnings) ? data.warnings.warnings : []),
    [data]
  );
  const summary = data?.summary;

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return warnings
      .filter((w) => severity === 'ALL' || String(w.overall_severity).toUpperCase() === severity)
      .filter(
        (w) =>
          !term ||
          String(w.district).toLowerCase().includes(term) ||
          String(w.message || '').toLowerCase().includes(term)
      )
      .sort((a, b) => {
        const sa = SEVERITY_ORDER[String(a.overall_severity).toUpperCase()] ?? 9;
        const sb = SEVERITY_ORDER[String(b.overall_severity).toUpperCase()] ?? 9;
        if (sa !== sb) return sa - sb;
        return String(a.district).localeCompare(String(b.district));
      });
  }, [warnings, severity, search]);

  const handleSend = async () => {
    setSending(true);
    try {
      const result = await sendWarningReport();
      toast.success(result?.message || 'Warning report request sent.');
    } catch (err) {
      if (err.status === 401 || err.status === 403) {
        toast.error('Your session has expired. Please sign in again.');
      } else {
        toast.error(err.message || 'Unable to send the warning report.');
      }
    } finally {
      setSending(false);
    }
  };

  const filterOptions = [
    { value: 'ALL', label: 'All', count: summary?.warning_count ?? warnings.length },
    { value: 'CRITICAL', label: 'Critical', count: summary?.critical_count },
    { value: 'HIGH', label: 'High', count: summary?.high_count },
  ];

  return (
    <div className="min-h-screen">
      <Navbar
        title="Early Warning"
        subtitle="Districts flagged in the current warning cycle."
      />

      <div className="space-y-5 p-4 md:p-6">
        <AsyncBoundary
          loading={loading}
          error={error}
          data={data}
          onRetry={reload}
          loadingMessage="Loading early warnings..."
          emptyTitle="No warnings available"
          emptyMessage="The backend returned no early warnings."
        >
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-secondary/15 bg-secondary/5 px-4 py-4 md:px-5">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-secondary">
                  Active warning cycle
                </p>
                <p className="mt-1 text-xl font-bold text-primary md:text-2xl">
                  {isPresent(summary?.warning_count)
                    ? `${formatNumber(summary.warning_count)} active warnings`
                    : `${warnings.length} active warnings`}
                </p>
                <p className="mt-1 text-base text-slate-600">
                  Warnings do not depend on the district, year or month selected on other pages.
                </p>
              </div>
              <button
                type="button"
                onClick={handleSend}
                disabled={sending}
                className="inline-flex items-center gap-2 rounded-full bg-secondary px-5 py-2.5 text-base font-semibold text-white shadow transition hover:bg-secondary/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Mail size={18} />
                {sending ? 'Sending...' : 'Send warning report'}
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <MetricTile
                label="Total warnings"
                value={formatNumber(summary?.warning_count ?? warnings.length)}
                accent="#6C5CE7"
              />
              <MetricTile
                label="Critical"
                value={formatNumber(summary?.critical_count)}
                accent="#E74C3C"
              />
              <MetricTile
                label="High"
                value={formatNumber(summary?.high_count)}
                accent="#F39C12"
              />
            </div>

            <Card
              title="Warning list"
              subtitle={`${visible.length} of ${warnings.length} districts shown`}
              action={
                <div className="flex flex-wrap items-center gap-3">
                  <div className="inline-flex gap-1 rounded-full border border-slate-200 bg-white p-1">
                    {filterOptions.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setSeverity(opt.value)}
                        className={`rounded-full px-3.5 py-1.5 text-base font-semibold transition ${
                          severity === opt.value
                            ? 'bg-secondary text-white shadow'
                            : 'text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        {opt.label}
                        {isPresent(opt.count) ? ` (${opt.count})` : ''}
                      </button>
                    ))}
                  </div>
                  <div className="relative">
                    <Search
                      size={18}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                    <input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search district"
                      className="w-56 rounded-full border border-slate-200 bg-white py-2 pl-10 pr-3 text-base outline-none focus:border-secondary"
                    />
                  </div>
                </div>
              }
            >
              {visible.length === 0 ? (
                <p className="rounded-xl bg-surface px-4 py-8 text-center text-base text-slate-500">
                  No warnings match the current filter.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[980px] text-base">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-sm text-slate-500">
                        <th className="w-8 pb-2" />
                        <th className="pb-2 pr-3 font-semibold">District</th>
                        <th className="pb-2 pr-3 font-semibold">Severity</th>
                        <th className="pb-2 pr-3 font-semibold">Triggered horizons</th>
                        <th className="pb-2 pr-3 font-semibold">Nearest warning</th>
                        <th className="pb-2 pr-3 font-semibold">Message</th>
                        <th className="pb-2 font-semibold">Recommended action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visible.map((w) => {
                        const isOpen = expanded === w.district;
                        return (
                          <Fragment key={w.district}>
                            <tr
                              onClick={() => setExpanded(isOpen ? null : w.district)}
                              className="cursor-pointer border-b border-slate-50 align-top transition hover:bg-slate-50"
                            >
                              <td className="py-3 text-slate-400">
                                {isOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                              </td>
                              <td className="py-3 pr-3 font-semibold text-primary">{w.district}</td>
                              <td className="py-3 pr-3">
                                <Pill className={severityBadgeClass(w.overall_severity)}>
                                  {w.overall_severity}
                                </Pill>
                              </td>
                              <td className="py-3 pr-3">
                                <div className="flex flex-wrap gap-1">
                                  {(w.triggered_horizons || []).map((h) => (
                                    <Pill key={h} className="bg-secondary/10 text-secondary">
                                      H{h}
                                    </Pill>
                                  ))}
                                  {!(w.triggered_horizons || []).length && '-'}
                                </div>
                              </td>
                              <td className="py-3 pr-3">
                                {isPresent(w.nearest_warning_horizon)
                                  ? `H${w.nearest_warning_horizon} - ${
                                      w.nearest_warning_month_display ||
                                      targetLabel(w.nearest_warning_month)
                                    }`
                                  : '-'}
                              </td>
                              <td className="py-3 pr-3 text-slate-700">{w.message || '-'}</td>
                              <td className="py-3 text-slate-700">{w.action || '-'}</td>
                            </tr>
                            {isOpen && (
                              <tr className="border-b border-slate-100 bg-surface">
                                <td colSpan={7} className="px-4 py-4">
                                  <HorizonMetrics horizons={w.horizons} />
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
              <p className="mt-3 text-sm text-slate-500">
                Select a row to see H1, H3 and H6 metrics. Warnings are forecast-based planning
                signals, not clinical diagnoses.
              </p>
            </Card>

            <div>
              <button
                type="button"
                onClick={() => {
                  reload();
                  refreshWarnings();
                }}
                className="rounded-full border border-slate-200 bg-white px-5 py-2 text-base font-semibold text-primary hover:bg-slate-50"
              >
                Refresh warnings
              </button>
            </div>
          </div>
        </AsyncBoundary>
      </div>
    </div>
  );
}
