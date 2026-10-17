import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, CheckCircle2, ChevronRight, CircleDashed } from 'lucide-react';
import { COMPONENTS, componentById } from '../../config/components';
import { useApi } from '../../lib/useApi';
import { Badge, Card, CardBody, CardHeader, DecisionBadge, ErrorBox, Loading, PageHeader, pct } from '../../ui';

function Status({ ok, label }) {
  return ok ? (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-success"><CheckCircle2 size={14} /> {label}</span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-muted"><CircleDashed size={14} /> {label}</span>
  );
}

function ComponentCard({ id, loading, error, status, children }) {
  const c = componentById[id];
  return (
    <Card className="flex flex-col overflow-hidden">
      <div className={`h-1 ${c.bg}`} />
      <div className="flex items-start gap-3 px-5 pt-4">
        <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${c.soft}`}>
          <c.icon size={20} className={c.text} />
        </span>
        <div className="min-w-0">
          <p className={`text-xs font-semibold uppercase tracking-wider ${c.text}`}>Component {c.number}</p>
          <h3 className="font-semibold leading-tight text-primary">{c.title}</h3>
          <p className="mt-0.5 text-[13px] text-muted">{c.question}</p>
        </div>
      </div>
      <div className="flex-1 px-5 py-4">
        {loading ? <Loading /> : error ? <p className="text-sm text-danger">Not reachable: {error.message}</p> : children}
      </div>
      <div className="flex items-center justify-between border-t border-line px-5 py-3">
        {status}
        <Link to={c.path} className={`inline-flex items-center gap-1 text-sm font-semibold ${c.text} hover:underline`}>
          Open <ArrowRight size={15} />
        </Link>
      </div>
    </Card>
  );
}

function Metric({ label, value, tone }) {
  const color = tone === 'danger' ? 'text-danger' : tone === 'warning' ? 'text-warning' : 'text-primary';
  return (
    <div>
      <p className={`tabular text-xl font-semibold ${color}`}>{value}</p>
      <p className="text-xs text-muted">{label}</p>
    </div>
  );
}

function Flow() {
  const step = (id, text) => {
    const c = componentById[id];
    return (
      <Link to={c.path} className="block h-full rounded-lg border border-line bg-white p-3 transition hover:shadow-card">
        <p className={`text-xs font-semibold ${c.text}`}>C{c.number} · {c.title}</p>
        <p className="mt-0.5 text-[13px] text-muted">{text}</p>
      </Link>
    );
  };
  const arrow = (dir = 'right') => (
    <div className="hidden items-center justify-center text-slate-400 md:flex">
      <ChevronRight size={18} className={dir === 'down' ? 'rotate-90' : ''} />
    </div>
  );
  return (
    <div className="grid gap-2 md:grid-cols-[1fr_24px_1fr_24px_1fr] md:grid-rows-[auto_20px_auto]">
      <div className="rounded-lg bg-slate-100 p-3">
        <p className="text-xs font-semibold text-primary">Child records</p>
        <p className="mt-0.5 text-[13px] text-muted">PHM growth registers and household surveys</p>
      </div>
      {arrow()}
      {step('c1', "Predicts each child's risk a year ahead")}
      {arrow()}
      {step('c2', 'Suggests feasible, reviewable changes')}
      <div className="hidden md:col-start-3 md:row-start-2 md:flex md:items-center md:justify-center">
        <span className="text-[11px] font-medium text-c3">↑ monitors and maintains</span>
      </div>
      <div className="hidden md:col-start-1 md:row-start-2 md:flex md:items-center md:justify-center">
        <span className="text-[11px] font-medium text-c4">↓ district aggregates</span>
      </div>
      <div className="md:col-start-1 md:row-start-3">{step('c4', 'Forecasts district burden and Triposha demand')}</div>
      <div className="md:col-start-3 md:row-start-3">{step('c3', "Watches C1's model; fixes it only when reliability is harmed")}</div>
    </div>
  );
}

export default function Overview() {
  const c1 = useApi('/risk/status');
  const c2 = useApi('/interventions/status');
  const c3 = useApi('/maintenance/live/status');
  const c4 = useApi('/forecast/warnings/summary');
  const last = c3.data?.last_cycle;
  const warnings = c4.data?.latest_warnings || [];

  return (
    <div className="animate-fade-in space-y-6">
      <PageHeader
        title="Overview"
        subtitle="One view of the four research components: what each one sees right now, and what needs attention."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ComponentCard id="c1" {...c1} status={<Status ok={c1.data?.ready} label={c1.data?.ready ? 'Model service ready' : 'Clinical app runs separately'} />}>
          <p className="text-sm text-muted">
            Risk prediction for underweight, stunting and MAM/SAM. The clinical app (child registration, visits,
            trajectories) runs as its own service.
          </p>
        </ComponentCard>

        <ComponentCard id="c2" {...c2} status={<Status ok={c2.data?.test_engine_ready} label={c2.data?.test_engine_ready ? 'Engine ready (test mode)' : 'Not ready'} />}>
          <div className="grid grid-cols-2 gap-3">
            <Metric label="search methods" value={c2.data?.methods?.length ?? '—'} />
            <Metric label="C1 model linked" value={c2.data?.c1_integrated ? 'Yes' : 'Not yet'} />
          </div>
        </ComponentCard>

        <ComponentCard id="c3" {...c3} status={<Status ok={c3.data?.ready} label={c3.data?.ready ? `Monitoring ${c3.data?.active_model?.version}` : 'Data not available'} />}>
          <div className="grid grid-cols-2 gap-3">
            <Metric label="balanced accuracy at deployment" value={pct(c3.data?.baseline?.bal_acc)} />
            <Metric label="batches awaiting outcomes" value={c3.data?.batches_awaiting_outcomes ?? '—'} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted">Last decision:</span>
            {last ? <DecisionBadge decision={last.decision} /> : <span className="text-muted">none yet</span>}
            {c3.data?.pending_approval && <Badge tone="warning">{c3.data.pending_approval} awaits approval</Badge>}
          </div>
        </ComponentCard>

        <ComponentCard id="c4" {...c4} status={<Status ok={!!c4.data} label={c4.data ? `Forecast from ${c4.data.forecast_origin}` : 'No forecast'} />}>
          <div className="grid grid-cols-2 gap-3">
            <Metric label="critical districts" value={c4.data?.critical_count ?? '—'} tone="danger" />
            <Metric label="high-risk districts" value={c4.data?.high_count ?? '—'} tone="warning" />
          </div>
        </ComponentCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader title="How the components work together" subtitle="Click a step to open that component" />
          <CardBody><Flow /></CardBody>
        </Card>

        <Card>
          <CardHeader title="Needs attention" icon={AlertTriangle} />
          <CardBody className="space-y-2.5">
            {last && last.decision !== 'no_action' && (
              <Link to="/c3/live" className="flex items-start gap-3 rounded-lg border border-violet-200 bg-violet-50/60 p-3 hover:bg-violet-50">
                <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-c3" />
                <span className="text-sm">
                  <span className="font-semibold text-primary">Model reliability: </span>
                  <span className="text-muted">{last.reason}</span>
                </span>
              </Link>
            )}
            {c4.error && <ErrorBox error={c4.error} />}
            {warnings.slice(0, 5).map((w) => (
              <Link key={w.district} to="/c4/early-warning" className="flex items-start gap-3 rounded-lg border border-line p-3 hover:bg-slate-50">
                <span className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${w.overall_severity === 'CRITICAL' ? 'bg-danger' : 'bg-warning'}`} />
                <span className="text-sm">
                  <span className="font-semibold text-primary">{w.district}</span>{' '}
                  <Badge tone={w.overall_severity === 'CRITICAL' ? 'danger' : 'warning'}>{w.overall_severity.toLowerCase()}</Badge>
                  <span className="block text-muted">Expected from {w.nearest_warning_month_display}</span>
                </span>
              </Link>
            ))}
            {!warnings.length && !(last && last.decision !== 'no_action') && !c4.loading && (
              <p className="py-4 text-center text-sm text-muted">Nothing needs attention right now.</p>
            )}
          </CardBody>
        </Card>
      </div>

      <p className="text-center text-xs text-muted">
        {COMPONENTS.map((c) => `C${c.number} ${c.owner}`).join(' · ')} — research prototype; predictions need professional review.
      </p>
    </div>
  );
}
