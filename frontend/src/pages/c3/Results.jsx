import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { useApi } from '../../lib/useApi';
import { API_BASE_URL } from '../../config/api';
import { Card, CardBody, CardHeader, ErrorBox, Loading, PageHeader, Stat, pct } from '../../ui';

const STRATEGY_LABEL = {
  static: 'Static (never update)',
  periodic_retrain: 'Periodic retraining',
  always_recalibrate: 'Always recalibrate',
  always_retrain: 'Always retrain',
  adaptive: 'Adaptive (C3)',
};

const FIGURE_TEXT = {
  'drift_vs_harm.png': ['Data changed vs model harmed', 'Each dot is one shift run. Drift (across) explains only about 18% of the real accuracy drop (up): big drift can be harmless, small drift can hurt.'],
  'harm_by_strength.png': ['How harm grows with each problem', 'Mean drop in balanced accuracy at each strength (±1 SD over 5 repeats); the dashed line is the 0.05 harm limit.'],
  'strategy_comparison.png': ['Maintenance strategies compared', 'C3 (green) makes the fewest unnecessary changes at a fraction of the retraining cost, with the same final accuracy.'],
};

const FIGURE_ORDER = ['drift_vs_harm.png', 'strategy_comparison.png', 'harm_by_strength.png'];

export default function Results() {
  const runs = useApi('/maintenance/results');
  const [which, setWhich] = useState('c3_underweight_calibrated');
  const run = runs.data?.find((r) => r.run === which) || runs.data?.[0];
  const adaptive = run?.strategy_summary.find((r) => r.strategy === 'adaptive');
  const periodic = run?.strategy_summary.find((r) => r.strategy === 'periodic_retrain');

  return (
    <div className="animate-fade-in space-y-5">
      <PageHeader
        component="c3"
        title="Experiment results"
        subtitle="160 shift runs on real linked data (120 stress tests + 40 unseen PHM areas), 800 maintenance cycles, underweight predicted a year ahead."
        actions={runs.data && (
          <div className="inline-flex rounded-lg border border-line bg-white p-1 text-sm">
            {runs.data.map((r) => (
              <button key={r.run} type="button" onClick={() => setWhich(r.run)}
                className={`rounded-md px-3 py-1.5 font-semibold transition ${run?.run === r.run ? 'bg-c3 text-white' : 'text-muted hover:text-primary'}`}>
                {r.drift_limits === 'calibrated' ? 'Data-driven drift limits' : 'Standard drift limits'}
              </button>
            ))}
          </div>
        )}
      />
      {runs.error && <ErrorBox error={runs.error} />}
      {runs.loading && <Loading />}

      {run && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Card><CardBody><Stat label="C3 intervention rate" value={pct(adaptive?.intervention_rate, 0)} hint={`periodic retraining: ${pct(periodic?.intervention_rate, 0)}`} /></CardBody></Card>
            <Card><CardBody><Stat label="Unnecessary changes (harmless shifts)" value={pct(adaptive?.unnecessary_interventions_when_harmless, 0)} hint={`periodic retraining: ${pct(periodic?.unnecessary_interventions_when_harmless, 0)}`} /></CardBody></Card>
            <Card><CardBody><Stat label="Mean maintenance cost" value={adaptive?.mean_cost?.toFixed(2)} hint={`periodic retraining: ${periodic?.mean_cost?.toFixed(2)}`} /></CardBody></Card>
            <Card><CardBody><Stat label="False alarms (current drift rules)" value={pct(run.suggested_thresholds?.current_rules_false_alarm_rate, 0)} hint="alarms raised on harmless shifts" /></CardBody></Card>
          </div>

          <Card>
            <CardHeader title="Strategy comparison" subtitle="All 160 shift runs"
              action={<a href={`${API_BASE_URL}${run.report}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-c3 hover:underline">Full report <ExternalLink size={14} /></a>} />
            <CardBody className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="text-left text-muted">
                  <tr>
                    <th className="pb-2 font-medium">Strategy</th>
                    <th className="pb-2 text-right font-medium">Intervened</th>
                    <th className="pb-2 text-right font-medium">Unneeded (harmless)</th>
                    <th className="pb-2 text-right font-medium">Corrected (harmful)</th>
                    <th className="pb-2 text-right font-medium">Escalated (harmful)</th>
                    <th className="pb-2 text-right font-medium">Cost</th>
                    <th className="pb-2 text-right font-medium">Bal. acc. after harmful</th>
                  </tr>
                </thead>
                <tbody className="tabular">
                  {run.strategy_summary.map((r) => (
                    <tr key={r.strategy} className={`border-t border-line ${r.strategy === 'adaptive' ? 'bg-violet-50/60 font-semibold text-c3' : ''}`}>
                      <td className="py-2">{STRATEGY_LABEL[r.strategy] || r.strategy}</td>
                      <td className="py-2 text-right">{pct(r.intervention_rate, 0)}</td>
                      <td className="py-2 text-right">{pct(r.unnecessary_interventions_when_harmless, 0)}</td>
                      <td className="py-2 text-right">{pct(r.corrected_when_harmful, 0)}</td>
                      <td className="py-2 text-right">{pct(r.escalated_when_harmful, 0)}</td>
                      <td className="py-2 text-right">{r.mean_cost?.toFixed(2)}</td>
                      <td className="py-2 text-right">{r.test_bal_acc_after_harmful?.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>

          <div className="grid gap-5 xl:grid-cols-2">
            {[...run.figures].sort((a, b) => FIGURE_ORDER.indexOf(a.split('/').pop()) - FIGURE_ORDER.indexOf(b.split('/').pop())).map((src) => {
              const name = src.split('/').pop();
              const [title, text] = FIGURE_TEXT[name] || [name, ''];
              return (
                <Card key={src} className={name === 'harm_by_strength.png' ? 'xl:col-span-2' : ''}>
                  <CardHeader title={title} subtitle={text} />
                  <CardBody><img src={`${API_BASE_URL}${src}`} alt={title} className="w-full rounded-lg" loading="lazy" /></CardBody>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
