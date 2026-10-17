import { useEffect, useMemo, useState } from 'react';
import Navbar from '../../components/layout/Navbar';
import AsyncBoundary from '../../components/component4/AsyncBoundary';
import PriorityMap from '../../components/component4/PriorityMap';
import SelectionRequiredNotice from '../../components/component4/SelectionRequiredNotice';
import SelectionSummary from '../../components/component4/SelectionSummary';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import ErrorState from '../../components/common/ErrorState';
import { Card, Pill, Stat, Tabs } from '../../components/component4/ui';
import useC4Data, { useBoundaries } from '../../components/component4/useC4Data';
import { useComponent4Selection } from '../../context/Component4SelectionContext';
import { getPriorityMapBySelectedMonth } from '../../services/component4/mapApi';
import {
  formatCases,
  formatNumber,
  priorityBadgeClass,
} from '../../components/component4/utils';
import {
  HORIZON_KEYS,
  HORIZON_META,
  formatPercent,
  isPresent,
  normalizeDistrictName,
  targetLabel,
  yearMonthShort,
} from '../../components/component4/format';

function DistrictPanel({ record, horizonKey }) {
  if (!record) {
    return (
      <Card title="Selected district">
        <p className="text-base text-slate-500">
          No priority record for the selected district at this horizon. Click a district on the map
          or in the list.
        </p>
      </Card>
    );
  }

  return (
    <Card
      title={record.district}
      subtitle={`${HORIZON_META[horizonKey].label} - ${targetLabel(record.target_date)}`}
      action={
        <Pill className={priorityBadgeClass(record.priority_level)}>{record.priority_level}</Pill>
      }
    >
      <div className="grid grid-cols-2 gap-2">
        {isPresent(record.priority_rank) && (
          <Stat label="Priority rank" value={`#${record.priority_rank}`} />
        )}
        {isPresent(record.dmbi_score) && (
          <Stat label="DMBI score" value={formatNumber(record.dmbi_score, 1)} />
        )}
        {isPresent(record.predicted_cases) && (
          <Stat label="Predicted cases" value={formatCases(record.predicted_cases)} />
        )}
        {isPresent(record.cases_per_1000_u5) && (
          <Stat label="Cases per 1,000 under-5" value={formatNumber(record.cases_per_1000_u5, 2)} />
        )}
        {isPresent(record.yoy_growth_percent) && (
          <Stat label="YoY burden growth" value={formatPercent(record.yoy_growth_percent)} />
        )}
        {isPresent(record.lower_95) && isPresent(record.upper_95) && (
          <Stat
            label="95% interval"
            value={`${formatCases(record.lower_95)} - ${formatCases(record.upper_95)}`}
          />
        )}
        {isPresent(record.uncertainty_level) && (
          <Stat label="Uncertainty" value={record.uncertainty_level} />
        )}
        {isPresent(record.confidence_label) && (
          <Stat label="Confidence" value={record.confidence_label} />
        )}
      </div>
      {record.priority_interpretation && (
        <p className="mt-3 text-sm text-slate-600">{record.priority_interpretation}</p>
      )}
      {record.uncertainty_interpretation && (
        <p className="mt-2 text-sm text-slate-500">{record.uncertainty_interpretation}</p>
      )}
    </Card>
  );
}

export default function GISPriorityMapPage() {
  const { district, year, month, hasSelection } = useComponent4Selection();
  const [horizonKey, setHorizonKey] = useState('h1');
  const [focusedDistrict, setFocusedDistrict] = useState(district);

  useEffect(() => {
    setFocusedDistrict(district);
  }, [district]);

  const { data, loading, error, reload } = useC4Data(
    () => getPriorityMapBySelectedMonth({ year, month }),
    [year, month],
    { enabled: hasSelection }
  );
  const boundaryState = useBoundaries();

  const availableKeys = HORIZON_KEYS.filter((key) => data?.priority_maps?.[key]);
  const activeKey = availableKeys.includes(horizonKey) ? horizonKey : availableKeys[0] || 'h1';
  const activeMap = data?.priority_maps?.[activeKey];

  const sortedDistricts = useMemo(() => {
    const list = Array.isArray(activeMap?.districts) ? [...activeMap.districts] : [];
    return list.sort((a, b) => {
      const ra = isPresent(a.priority_rank) ? Number(a.priority_rank) : Infinity;
      const rb = isPresent(b.priority_rank) ? Number(b.priority_rank) : Infinity;
      return ra - rb;
    });
  }, [activeMap]);

  const selectedRecord = sortedDistricts.find(
    (r) => normalizeDistrictName(r.district) === normalizeDistrictName(focusedDistrict)
  );

  return (
    <div className="min-h-screen">
      <Navbar
        title="GIS Risk Map"
        subtitle="District priority levels across Sri Lanka."
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
            isEmpty={!availableKeys.length}
            loadingMessage="Loading district priorities..."
            emptyTitle="No map data for this month"
            emptyMessage="The backend has no GIS priority data for the selected year and month."
          >
            <div className="space-y-5">
              <SelectionSummary />

              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-base text-slate-600">
                  All horizons are generated automatically - the tabs only switch the view.
                </p>
                <Tabs
                  value={activeKey}
                  onChange={setHorizonKey}
                  options={availableKeys.map((key) => ({
                    value: key,
                    label: `${HORIZON_META[key].label} - ${yearMonthShort(
                      data.priority_maps[key].target_year,
                      data.priority_maps[key].target_month
                    )}`,
                  }))}
                />
              </div>

              <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                <Card
                  className="xl:col-span-2"
                  title={`Priority map - ${HORIZON_META[activeKey].label}`}
                  subtitle={`Target month ${yearMonthShort(
                    activeMap?.target_year,
                    activeMap?.target_month
                  )}. Click a district to inspect it.`}
                >
                  {boundaryState.loading ? (
                    <LoadingSpinner message="Loading district boundaries..." />
                  ) : boundaryState.error ? (
                    <ErrorState
                      title="Unable to load district boundaries"
                      message={boundaryState.error.message}
                    />
                  ) : (
                    <PriorityMap
                      boundaries={boundaryState.boundaries}
                      districts={sortedDistricts}
                      selectedDistrict={focusedDistrict}
                      onSelectDistrict={setFocusedDistrict}
                      horizonKey={activeKey}
                      height={420}
                    />
                  )}
                </Card>

                <DistrictPanel record={selectedRecord} horizonKey={activeKey} />
              </div>

              <Card
                title="Districts by priority rank"
                subtitle={`${sortedDistricts.length} districts - ${HORIZON_META[activeKey].label}`}
              >
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-base">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-sm text-slate-500">
                        <th className="pb-2 pr-3 font-semibold">Rank</th>
                        <th className="pb-2 pr-3 font-semibold">District</th>
                        <th className="pb-2 pr-3 font-semibold">Priority</th>
                        <th className="pb-2 pr-3 font-semibold">DMBI</th>
                        <th className="pb-2 pr-3 font-semibold">Predicted cases</th>
                        <th className="pb-2 font-semibold">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedDistricts.map((r) => {
                        const isSelected =
                          normalizeDistrictName(r.district) ===
                          normalizeDistrictName(focusedDistrict);
                        return (
                          <tr
                            key={r.district}
                            onClick={() => setFocusedDistrict(r.district)}
                            className={`cursor-pointer border-b border-slate-50 transition hover:bg-slate-50 ${
                              isSelected ? 'bg-secondary/5' : ''
                            }`}
                          >
                            <td className="py-2.5 pr-3 font-semibold text-slate-500">
                              {isPresent(r.priority_rank) ? `#${r.priority_rank}` : '-'}
                            </td>
                            <td className="py-2.5 pr-3 font-semibold text-primary">{r.district}</td>
                            <td className="py-2.5 pr-3">
                              <Pill className={priorityBadgeClass(r.priority_level)}>
                                {r.priority_level}
                              </Pill>
                            </td>
                            <td className="py-2.5 pr-3">{formatNumber(r.dmbi_score, 1)}</td>
                            <td className="py-2.5 pr-3">{formatCases(r.predicted_cases)}</td>
                            <td className="py-2.5">{r.confidence_label || '-'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          </AsyncBoundary>
        )}
      </div>
    </div>
  );
}
