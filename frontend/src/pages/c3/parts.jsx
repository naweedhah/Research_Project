import { Badge, Card, CardBody, CardHeader, DecisionBadge, KeyValues, num, pct } from '../../ui';

/* Panels shared by the Model health (demonstration) and Live monitoring pages: one maintenance cycle's evidence. */

export function DecisionPanel({ cycle }) {
  return (
    <Card>
      <CardHeader title="Decision" subtitle={cycle.scenario ? `Scenario: ${cycle.scenario}` : undefined} />
      <CardBody className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <DecisionBadge decision={cycle.decision} />
          <span className="text-sm text-muted">model {cycle.model_before} → {cycle.model_after}</span>
          {cycle.promoted && <Badge tone="success">deployed</Badge>}
          {cycle.pending_approval && <Badge tone="warning">waiting for approval</Badge>}
        </div>
        <p className="text-[15px] text-primary">{cycle.reason}</p>
        {cycle.possible_causes?.length > 0 && (
          <p className="text-sm text-muted">
            <span className="font-semibold text-primary">Possible causes: </span>
            {cycle.possible_causes.join('; ')}
          </p>
        )}
      </CardBody>
    </Card>
  );
}

export function DriftPanel({ drift }) {
  const flagged = drift?.flagged_features || [];
  return (
    <Card>
      <CardHeader title="What changed (drift)" subtitle={flagged.length ? `${flagged.length} inputs flagged` : 'No input flagged'} />
      <CardBody>
        <KeyValues rows={[['Any drift flagged', drift?.any_flagged ? 'yes' : 'no'], ['Prediction drift (PSI)', num(drift?.prediction_psi)]]} />
        {flagged.length > 0 && (
          <ul className="mt-3 max-h-60 divide-y divide-line overflow-auto rounded-lg border border-line">
            {flagged.map((f) => (
              <li key={f.feature} className="px-3 py-2">
                <p className="text-[13px] font-semibold text-primary">{f.feature}</p>
                <p className="tabular break-words text-xs text-muted">{f.reasons.join(' · ')}</p>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

export function ReliabilityPanel({ cycle }) {
  const r = cycle.reliability || {};
  const m = r.metrics || {};
  const lf = cycle.label_free_warning;
  const urgencyTone = { high: 'danger', medium: 'warning', low: 'success' };
  return (
    <Card>
      <CardHeader title="Did it hurt? (reliability)" subtitle={r.status === 'pending_labels' ? 'Outcomes not known yet' : undefined} />
      <CardBody>
        {r.status === 'pending_labels' ? (
          <div className="space-y-3">
            <p className="text-sm text-muted">Accuracy cannot be measured until outcomes arrive. The label-free warning ranks how urgent this is.</p>
            {lf && (
              <KeyValues rows={[
                ['Urgency', <Badge key="u" tone={urgencyTone[lf.urgency]}>{lf.urgency}</Badge>],
                ['Children flagged', `${pct(lf.flagged_rate_reference)} → ${pct(lf.flagged_rate_current)}`],
                ['Mean predicted risk', `${pct(lf.mean_risk_reference)} → ${pct(lf.mean_risk_current)}`],
              ]} />
            )}
          </div>
        ) : (
          <KeyValues rows={[
            ['Reliable', r.reliable ? <Badge key="r" tone="success">yes</Badge> : <Badge key="r" tone="danger">no</Badge>],
            ['Balanced accuracy', pct(m.recall_macro)],
            ['Sensitivity', pct(m.recall_per_class?.['1'])],
            ['ROC-AUC', num(m.auroc)],
            ['Calibration error', num(m.ece)],
            cycle.test_after_cycle && ['Unseen children after cycle', `${pct(cycle.test_after_cycle.bal_acc)} balanced accuracy`],
          ]} />
        )}
      </CardBody>
    </Card>
  );
}

export function ContextPanel({ context }) {
  return (
    <Card>
      <CardHeader title="External context" subtitle="Disasters, food prices, inflation" />
      <CardBody>
        {!context ? (
          <p className="text-sm text-muted">Not included in this cycle.</p>
        ) : context.signals?.length ? (
          <div className="space-y-2">
            {context.signals.map((s, i) => (
              <p key={i} className="flex items-start gap-2 text-sm">
                <Badge tone={s.level === 'alert' ? 'danger' : 'warning'}>{s.level}</Badge>
                <span className="text-primary">{s.summary}</span>
              </p>
            ))}
            {context.heightened && <p className="text-xs text-muted">Alert active → drift limits tightened for this cycle. Context never triggers maintenance by itself.</p>}
          </div>
        ) : (
          <p className="text-sm text-muted">No signals for {context.window}.</p>
        )}
      </CardBody>
    </Card>
  );
}

export function SafetyPanel({ cycle }) {
  const v = cycle.validation?.adapt || cycle.validation?.current;
  const ver = cycle.verification;
  const sh = cycle.shadow;
  return (
    <Card>
      <CardHeader title="Safety checks" />
      <CardBody>
        <KeyValues rows={[
          ['Invalid records', v ? `${v.invalid_rows} of ${v.rows}` : '—'],
          ['Candidate model', cycle.candidate || 'none'],
          ['Shadow agreement', sh ? `${pct(sh.agreement)} (flagged ${pct(sh.flagged_share_active)} → ${pct(sh.flagged_share_candidate)})` : '—'],
          ['Verification gate', ver ? (ver.passed ? <Badge key="v" tone="success">passed</Badge> : <Badge key="v" tone="danger">failed</Badge>) : '—'],
          ['Deployed', cycle.promoted ? 'yes' : cycle.pending_approval ? 'waiting for approval' : 'no'],
        ]} />
        {ver && !ver.passed && (
          <ul className="mt-3 space-y-1 rounded-lg bg-orange-50 px-3 py-2 text-[13px] text-danger">
            {ver.failures.map((f) => <li key={f} className="tabular">{f}</li>)}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

export function SubgroupPanel({ metrics }) {
  const sg = metrics?.subgroups;
  const groups = sg?.groups ? Object.entries(sg.groups) : [];
  return (
    <Card>
      <CardHeader title="Subgroups" subtitle="A new model may not make the worst-off group more than 5 points worse" />
      <CardBody>
        {!groups.length ? (
          <p className="text-sm text-muted">Not measurable for this cycle.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-muted">
              <tr><th className="pb-2 font-medium">Group</th><th className="pb-2 font-medium">Children</th><th className="pb-2 font-medium">Balanced accuracy</th><th className="pb-2 font-medium">Sensitivity</th></tr>
            </thead>
            <tbody>
              {groups.map(([g, x]) => (
                <tr key={g} className={`border-t border-line ${g === sg.worst_group ? 'font-semibold text-c3' : ''}`}>
                  <td className="py-1.5">{g}{g === sg.worst_group && ' (worst)'}</td>
                  <td className="tabular py-1.5">{x.n}</td>
                  <td className="tabular py-1.5">{pct(x.bal_acc)}</td>
                  <td className="tabular py-1.5">{pct(x.sensitivity)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardBody>
    </Card>
  );
}

export function CycleEvidence({ cycle }) {
  return (
    <div className="space-y-4">
      <DecisionPanel cycle={cycle} />
      <div className="grid gap-4 lg:grid-cols-2">
        <DriftPanel drift={cycle.drift} />
        <ReliabilityPanel cycle={cycle} />
        <ContextPanel context={cycle.context} />
        <SafetyPanel cycle={cycle} />
      </div>
      <SubgroupPanel metrics={cycle.reliability?.metrics} />
    </div>
  );
}

export function HistoryTable({ rows }) {
  const tone = { initial: 'neutral', promoted: 'success', rejected: 'danger', rollback: 'warning', pending_approval: 'info' };
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-muted">
        <tr><th className="pb-2 font-medium">Version</th><th className="pb-2 font-medium">Event</th><th className="pb-2 font-medium">Note</th></tr>
      </thead>
      <tbody>
        {[...rows].reverse().map((h, i) => (
          <tr key={i} className="border-t border-line align-top">
            <td className="tabular py-2 font-semibold">{h.version}</td>
            <td className="py-2"><Badge tone={tone[h.action] || 'neutral'}>{h.action.replace('_', ' ')}</Badge></td>
            <td className="py-2 text-muted">{h.reason || (h.verification_passed === false ? 'failed verification gate' : '')}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
