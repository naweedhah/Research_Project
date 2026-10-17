import { useState } from 'react';
import { ChevronRight, Terminal } from 'lucide-react';
import { useApi } from '../../lib/useApi';
import { Badge, Card, CardBody, CardHeader, DecisionBadge, Empty, ErrorBox, KeyValues, Loading, PageHeader, Stat, pct } from '../../ui';
import { CycleEvidence } from './parts';

/* The real workflow: screening batches arrive, outcomes follow months later. Data comes from /maintenance/live. */
export default function LiveMonitoring() {
  const status = useApi('/maintenance/live/status');
  const batches = useApi('/maintenance/live/batches');
  const [selected, setSelected] = useState(null);
  const detail = useApi(selected ? `/maintenance/live/batches/${encodeURIComponent(selected)}` : null);
  const s = status.data;
  const rows = [...(batches.data || [])].reverse();

  return (
    <div className="animate-fade-in space-y-5">
      <PageHeader
        component="c3"
        title="Live monitoring"
        subtitle="Each screening round is checked when it arrives (validation, drift, label-free urgency) and again when its outcomes are known (reliability, maintenance)."
      />
      {status.error && <ErrorBox error={status.error} />}

      {s?.ready && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card><CardBody><Stat label="Active model" value={s.active_model.version} hint={`${s.active_model.action}, ${s.active_model.training_records} training records`} /></CardBody></Card>
          <Card><CardBody><Stat label="Batches received" value={s.batches} hint={`${s.batches_awaiting_outcomes} waiting for outcomes`} /></CardBody></Card>
          <Card><CardBody><Stat label="Waiting for approval" value={s.pending_approval || 'none'} tone={s.pending_approval ? 'warning' : undefined} /></CardBody></Card>
          <Card><CardBody><Stat label="Post-deployment check" value={s.awaiting_post_deployment_check ? 'pending' : 'none due'} hint={s.awaiting_post_deployment_check ? `next outcomes check ${s.awaiting_post_deployment_check}` : 'runs on the first outcomes after a deployment'} /></CardBody></Card>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(360px,1fr)_1.6fr]">
        <Card>
          <CardHeader title="Screening batches" subtitle="Newest first; select one for its evidence" />
          <CardBody className="p-0">
            {batches.loading ? <div className="px-5"><Loading /></div> : !rows.length ? (
              <Empty>
                No batches yet. Send a round of held-out children from the C3 folder:
                <code className="mt-2 rounded bg-slate-100 px-2 py-1 text-xs text-primary">python -m component3.experiments.simulate_live --shift prevalence:0.4</code>
              </Empty>
            ) : (
              <ul className="divide-y divide-line">
                {rows.map((b) => (
                  <li key={b.batch_id}>
                    <button type="button" onClick={() => setSelected(b.batch_id)}
                      className={`flex w-full items-center gap-3 px-5 py-3 text-left transition hover:bg-slate-50 ${selected === b.batch_id ? 'bg-violet-50/60' : ''}`}>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-primary">{b.batch_id}</p>
                        <p className="text-xs text-muted">{b.records} children{b.area ? ` · ${b.area}` : ''} · {b.submitted.slice(0, 16).replace('T', ' ')}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <DecisionBadge decision={b.outcome_decision || b.decision} />
                        <span className="text-[11px] text-muted">{b.labelled ? 'outcomes in' : 'awaiting outcomes'}</span>
                      </div>
                      <ChevronRight size={16} className="text-slate-400" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <div className="space-y-4">
          {!selected ? (
            <Card>
              <CardHeader title="How the live workflow runs" icon={Terminal} />
              <CardBody className="space-y-3 text-sm text-muted">
                <p><span className="font-semibold text-primary">1. Batch arrives:</span> records are validated and compared with the model's training data. Without outcomes C3 never adapts; it gives a label-free urgency instead.</p>
                <p><span className="font-semibold text-primary">2. Outcomes arrive:</span> a newly deployed model is checked first (automatic rollback if worse). Then C3 assesses reliability and, if harmed, builds a candidate on part of the records and verifies it on the rest.</p>
                <p><span className="font-semibold text-primary">3. A person approves</span> any verified candidate before it goes live (see Versions & approvals).</p>
                {s?.thresholds && (
                  <KeyValues rows={[
                    ['Reliability limit', `balanced accuracy ≥ ${pct(s.thresholds.reliability_tau)}`],
                    ['Sensitivity floor', pct(s.thresholds.min_sensitivity)],
                    ['Calibration limit', `error ≤ ${s.thresholds.calibration_tau}`],
                  ]} />
                )}
              </CardBody>
            </Card>
          ) : detail.loading ? (
            <Card><CardBody><Loading /></CardBody></Card>
          ) : detail.error ? (
            <ErrorBox error={detail.error} />
          ) : detail.data && (
            <>
              <Card>
                <CardBody className="flex flex-wrap items-center gap-3 text-sm">
                  <span className="font-semibold text-primary">{detail.data.batch_id}</span>
                  <Badge>{detail.data.records} children</Badge>
                  {detail.data.collected_from && <Badge tone="info">{detail.data.collected_from} → {detail.data.collected_to}</Badge>}
                  {Object.keys(detail.data.unknown_categories || {}).length > 0 && (
                    <Badge tone="warning">unknown answers: {Object.entries(detail.data.unknown_categories).map(([k, v]) => `${k} (${v})`).join(', ')}</Badge>
                  )}
                  {detail.data.post_deployment_check?.checked && (
                    <Badge tone={detail.data.post_deployment_check.rolled_back ? 'danger' : 'success'}>
                      post-deployment check: {detail.data.post_deployment_check.rolled_back ? 'rolled back' : 'kept'} {detail.data.post_deployment_check.active_version}
                    </Badge>
                  )}
                </CardBody>
              </Card>
              {detail.data.outcome_cycle && (
                <>
                  <h2 className="pt-1 text-sm font-semibold uppercase tracking-wider text-muted">When outcomes arrived</h2>
                  <CycleEvidence cycle={detail.data.outcome_cycle} />
                </>
              )}
              <h2 className="pt-1 text-sm font-semibold uppercase tracking-wider text-muted">When the batch arrived</h2>
              <CycleEvidence cycle={detail.data.monitoring} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
