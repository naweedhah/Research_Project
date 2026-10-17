import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Check, Play, RotateCcw, Undo2, X } from 'lucide-react';
import { post, useApi } from '../../lib/useApi';
import { Button, Card, CardBody, CardHeader, ErrorBox, Loading, PageHeader, pct } from '../../ui';
import { CycleEvidence, HistoryTable } from './parts';

/* Demonstration sandbox: simulated shifts on real held-out children (in memory; Reset restores v1.0). */
export default function ModelHealth() {
  const status = useApi('/maintenance/status');
  const scenarios = useApi('/maintenance/scenarios');
  const history = useApi('/maintenance/history');
  const [form, setForm] = useState({ scenario: 'none|0', labels: true, approval: false, context: true, start: '2025-12-01', end: '2025-12-31', offline: true });
  const [cycle, setCycle] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status.data?.last_cycle && !cycle) setCycle(status.data.last_cycle);
  }, [status.data, cycle]);

  const refresh = () => {
    status.reload();
    history.reload();
  };

  const run = async () => {
    const [family, strength] = form.scenario.split('|');
    const body = { family, strength: Number(strength), with_labels: form.labels, require_approval: form.approval, offline_context: form.offline };
    if (form.context) Object.assign(body, { context_start: form.start, context_end: form.end });
    setBusy(true);
    try {
      setCycle(await post('/maintenance/cycle', body));
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
      refresh();
    }
  };

  const act = async (path, label, params) => {
    try {
      await post(path, undefined, params);
      toast.success(label);
      if (path === '/maintenance/reset') setCycle(null);
    } catch (e) {
      toast.error(e.message);
    }
    refresh();
  };

  const s = status.data;
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));
  const check = (k, label) => (
    <label className="flex items-center gap-2 text-sm text-primary">
      <input type="checkbox" className="h-4 w-4 accent-[var(--color-c3)]" checked={form[k]} onChange={set(k)} /> {label}
    </label>
  );

  return (
    <div className="animate-fade-in">
      <PageHeader
        component="c3"
        title="Model health"
        subtitle="Simulate what can happen to new data and watch C3 decide: no action, recalibrate, retrain or hold, and deploy only what passes every safety check."
      />
      {status.error && <ErrorBox error={status.error} hint="Start the backend with C3_DATA_DIR set to the data folder." />}
      {s && !s.ready && <ErrorBox error={s.reason || 'Model not ready'} />}

      {s?.ready && (
        <Card className="mb-5">
          <CardBody className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
            <span><span className="text-muted">Active model </span><span className="font-semibold">{s.active_version}</span></span>
            <span><span className="text-muted">Predicts </span><span className="font-semibold">{s.target}</span></span>
            <span><span className="text-muted">Balanced accuracy at deployment </span><span className="tabular font-semibold">{pct(s.baseline.bal_acc)}</span></span>
            <span><span className="text-muted">Sensitivity </span><span className="tabular font-semibold">{pct(s.baseline.sensitivity)}</span></span>
          </CardBody>
        </Card>
      )}

      <div className="grid gap-5 xl:grid-cols-[340px_1fr]">
        <div className="space-y-5">
          <Card>
            <CardHeader title="Run a maintenance cycle" />
            <CardBody className="space-y-3">
              <label className="block text-sm font-medium text-primary">
                What happened to the new data
                <select className="mt-1 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm" value={form.scenario} onChange={set('scenario')}>
                  {(scenarios.data || []).map((x) => (
                    <option key={`${x.family}|${x.strength}`} value={`${x.family}|${x.strength}`}>
                      {x.family.replaceAll('_', ' ')} — {x.label}
                    </option>
                  ))}
                </select>
              </label>
              {check('labels', 'Outcome labels available')}
              {check('approval', 'Require human approval before deployment')}
              {check('context', 'Include external context')}
              {form.context && (
                <div className="grid grid-cols-2 gap-2">
                  <input type="date" className="rounded-lg border border-line px-2 py-1.5 text-sm" value={form.start} onChange={set('start')} aria-label="Context start" />
                  <input type="date" className="rounded-lg border border-line px-2 py-1.5 text-sm" value={form.end} onChange={set('end')} aria-label="Context end" />
                </div>
              )}
              {form.context && check('offline', 'Use bundled context samples (offline)')}
              <div className="flex gap-2 pt-1">
                <Button variant="c3" className="flex-1" onClick={run} disabled={busy || !s?.ready}>
                  <Play size={15} /> {busy ? 'Running…' : 'Run cycle'}
                </Button>
                <Button variant="outline" onClick={() => act('/maintenance/reset', 'Model reset to v1.0')} title="Reset to v1.0">
                  <RotateCcw size={15} /> Reset
                </Button>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Deployment controls" subtitle={s?.pending_approval ? `${s.pending_approval} is waiting for approval` : 'No model waiting for approval'} />
            <CardBody className="flex flex-wrap gap-2">
              <Button variant="outline" disabled={!s?.pending_approval} onClick={() => act('/maintenance/approve', 'Approved and deployed', { approver: 'MOH officer' })}>
                <Check size={15} /> Approve
              </Button>
              <Button variant="outline" disabled={!s?.pending_approval} onClick={() => act('/maintenance/reject-pending', 'Candidate rejected')}>
                <X size={15} /> Reject
              </Button>
              <Button variant="danger" onClick={() => act('/maintenance/rollback', 'Rolled back')}>
                <Undo2 size={15} /> Roll back
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Model versions" />
            <CardBody>{history.data ? <HistoryTable rows={history.data} /> : <Loading />}</CardBody>
          </Card>
        </div>

        <div>
          {busy ? (
            <Card><CardBody><Loading label="Running monitor → assess → decide → adapt → verify…" /></CardBody></Card>
          ) : cycle ? (
            <CycleEvidence cycle={cycle} />
          ) : (
            <Card>
              <CardBody className="py-14 text-center">
                <p className="text-lg font-semibold text-primary">Run a cycle to see what C3 decides</p>
                <p className="mx-auto mt-1 max-w-md text-sm text-muted">
                  Each cycle takes real children the model never trained on, applies the chosen problem, and runs the full
                  loop: monitor, assess, decide, adapt, verify.
                </p>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
