import { useEffect, useMemo, useState } from 'react';
import { Info } from 'lucide-react';
import Navbar from '../../components/layout/Navbar';
import AsyncBoundary from '../../components/component4/AsyncBoundary';
import SelectionRequiredNotice from '../../components/component4/SelectionRequiredNotice';
import SelectionSummary from '../../components/component4/SelectionSummary';
import ShapChart from '../../components/component4/ShapChart';
import { Card, MetricTile, Pill, Tabs } from '../../components/component4/ui';
import useC4Data from '../../components/component4/useC4Data';
import { useComponent4Selection } from '../../context/Component4SelectionContext';
import { getExplainabilityBySelectedMonth } from '../../services/component4/explainabilityApi';
import { formatCases, formatNumber } from '../../components/component4/utils';
import {
  HORIZON_META,
  isPresent,
  targetLabel,
} from '../../components/component4/format';

function horizonKeyOf(item) {
  return `h${Number(item.horizon)}`;
}

export default function ExplainableAIPage() {
  const { district, year, month, selection, hasSelection } = useComponent4Selection();
  const [activeKey, setActiveKey] = useState('h1');

  const { data, loading, error, reload } = useC4Data(
    () => getExplainabilityBySelectedMonth(selection),
    [district, year, month],
    { enabled: hasSelection }
  );

  const items = useMemo(() => {
    const list = Array.isArray(data?.explanations) ? data.explanations : [];
    return [...list].sort((a, b) => Number(a.horizon) - Number(b.horizon));
  }, [data]);

  const tabOptions = items.map((item) => {
    const key = horizonKeyOf(item);
    return { value: key, label: HORIZON_META[key]?.label || key.toUpperCase() };
  });

  useEffect(() => {
    if (!items.length) return;
    if (!items.some((item) => horizonKeyOf(item) === activeKey)) {
      const h1 = items.find((item) => Number(item.horizon) === 1);
      setActiveKey(horizonKeyOf(h1 || items[0]));
    }
  }, [items, activeKey]);

  const active = items.find((item) => horizonKeyOf(item) === activeKey) || items[0];

  return (
    <div className="min-h-screen">
      <Navbar
        title="Explainable AI"
        subtitle="Which model components contributed to the forecast."
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
          isEmpty={!items.length}
          loadingMessage="Loading forecast explanation..."
          emptyTitle="No explanation for this selection"
          emptyMessage="The backend has no SHAP explanation for the selected district, year and month."
        >
          <div className="space-y-5">
            <SelectionSummary />

            {tabOptions.length > 1 && (
              <div className="flex flex-wrap items-center justify-end gap-3">
                <Tabs value={activeKey} onChange={setActiveKey} options={tabOptions} />
              </div>
            )}

            {active && (
              <>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <MetricTile
                    label={`${HORIZON_META[activeKey]?.label || ''} predicted cases`}
                    value={formatCases(active.predicted_cases)}
                    hint={active.target_date ? targetLabel(active.target_date) : undefined}
                  />
                  <MetricTile
                    label="Dominant domain"
                    value={
                      <span className="text-xl md:text-2xl">{active.dominant_domain || '-'}</span>
                    }
                    hint={active.dominant_domain_direction}
                    accent="#0B1F4D"
                  />
                  <MetricTile
                    label="Dominant domain contribution"
                    value={
                      isPresent(active.dominant_domain_shap)
                        ? `${active.dominant_domain_shap > 0 ? '+' : ''}${formatNumber(
                            active.dominant_domain_shap,
                            2
                          )}`
                        : '-'
                    }
                    hint="cases, relative to the model baseline"
                    accent="#F39C12"
                  />
                </div>

                <Card
                  title="Forecast explanation"
                  subtitle={`${HORIZON_META[activeKey]?.label || ''} - how the model arrived at this forecast`}
                  action={
                    active.dominant_domain_direction ? (
                      <Pill className="bg-secondary/10 text-secondary">
                        {active.dominant_domain_direction}
                      </Pill>
                    ) : null
                  }
                >
                  {active.explanation ? (
                    <p className="text-base leading-relaxed text-slate-700">
                      {active.explanation}
                    </p>
                  ) : (
                    <p className="text-base text-slate-500">
                      No explanation text was returned for this horizon.
                    </p>
                  )}
                </Card>

                <Card
                  title="Model contribution by component"
                  subtitle="Top increasing and decreasing components from the SHAP analysis"
                >
                  <ShapChart item={active} />
                </Card>
              </>
            )}

            <div className="flex items-start gap-3 rounded-2xl border border-secondary/15 bg-secondary/5 px-4 py-4">
              <Info size={20} className="mt-0.5 shrink-0 text-secondary" />
              <p className="text-base text-slate-700">
                SHAP values describe how the Random Forest model behaved for this forecast. They
                show model contribution, not proof that a factor caused the forecasted burden, and
                should support - not replace - professional judgement. District and geographic
                context is a model variable, not a modifiable risk factor.
              </p>
            </div>
          </div>
        </AsyncBoundary>
        )}
      </div>
    </div>
  );
}
