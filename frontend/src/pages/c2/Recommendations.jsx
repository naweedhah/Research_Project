import { useState } from 'react';
import toast from 'react-hot-toast';
import { ArrowRight, Info, Sparkles, UserCheck } from 'lucide-react';
import { post, useApi } from '../../lib/useApi';
import { Badge, Button, Card, CardBody, CardHeader, Empty, PageHeader } from '../../ui';

const FEATURES = { meals_per_day: 'Meals per day', dietary_diversity: 'Dietary diversity (food groups)' };
const CHECKS = {
  available: 'Food available locally',
  practical: 'Practical for the household',
  age_suitable: 'Suitable for the age',
  eligible: 'Eligible',
  clinically_suitable: 'Clinically suitable',
  transition_justified: 'Change justified',
};
const METHODS = {
  bounded_search: { label: 'Bounded search', predictor: null },
  dice: { label: 'DiCE (diverse counterfactuals)', predictor: 'synthetic_sklearn_grid_v1' },
  face_graph: { label: 'FACE (feasible paths)', predictor: null },
};

const allChecks = (value) => Object.fromEntries(Object.keys(CHECKS).map((k) => [k, { meals_per_day: value, dietary_diversity: value }]));
const TRI = { yes: true, no: false, unknown: null };
const triOf = (v) => (v === true ? 'yes' : v === false ? 'no' : 'unknown');

export default function Recommendations() {
  const status = useApi('/interventions/status');
  const [child, setChild] = useState({
    child_id: 'DEMO-001', age_months: 24, sex: 'female', birth_weight_kg: 2.8, historical_exclusive_breastfeeding: true,
    household_income_band: 'low', meals_per_day: 3, dietary_diversity: 3, supplement_use: false,
  });
  const [checks, setChecks] = useState(allChecks(true));
  const [budget, setBudget] = useState(10);
  const [method, setMethod] = useState('bounded_search');
  const [maxChanges, setMaxChanges] = useState(2);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const setC = (k, cast = (v) => v) => (e) => setChild((c) => ({ ...c, [k]: cast(e.target.value) }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { child_id, ...features } = child;
      const body = {
        child_id, mode: 'test', method, max_changes: maxChanges, max_cards: 5,
        child: { ...features, birth_weight_kg: features.birth_weight_kg === '' ? null : Number(features.birth_weight_kg) },
        context: { budget_units: budget === '' ? null : Number(budget), ...checks },
      };
      if (METHODS[method].predictor) body.predictor = METHODS[method].predictor;
      setResult(await post('/interventions/recommendations', body));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  const field = 'mt-1 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm outline-none focus:border-c2 focus:ring-2 focus:ring-c2/20';
  const label = 'block text-sm font-medium text-primary';

  return (
    <div className="animate-fade-in">
      <PageHeader
        component="c2"
        title="Intervention recommendations"
        subtitle="Small, feasible changes that would move the child to a lower-concern category, ranked and checked against local feasibility. Every card needs professional review."
        actions={status.data && <Badge tone="warning">Test mode · synthetic predictor</Badge>}
      />

      <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
        <form onSubmit={submit} className="space-y-5">
          <Card>
            <CardHeader title="Child" />
            <CardBody className="grid grid-cols-2 gap-3">
              <label className={`${label} col-span-2`}>Child ID (pseudonymous)<input className={field} value={child.child_id} onChange={setC('child_id')} required /></label>
              <label className={label}>Age (months)<input className={field} type="number" min="0" max="59" value={child.age_months} onChange={setC('age_months', Number)} required /></label>
              <label className={label}>Sex
                <select className={field} value={child.sex} onChange={setC('sex')}><option value="female">Female</option><option value="male">Male</option></select>
              </label>
              <label className={label}>Birth weight (kg)<input className={field} type="number" step="0.1" min="0.5" max="6" value={child.birth_weight_kg} onChange={setC('birth_weight_kg')} /></label>
              <label className={label}>Household income
                <select className={field} value={child.household_income_band} onChange={setC('household_income_band')}>
                  {['low', 'middle', 'high', 'unknown'].map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              </label>
              <label className={label}>Meals per day<input className={field} type="number" min="1" max="5" value={child.meals_per_day} onChange={setC('meals_per_day', Number)} required /></label>
              <label className={label}>Dietary diversity (0–5)<input className={field} type="number" min="0" max="5" value={child.dietary_diversity} onChange={setC('dietary_diversity', Number)} required /></label>
              <label className={label}>Exclusive breastfeeding
                <select className={field} value={triOf(child.historical_exclusive_breastfeeding)} onChange={(e) => setChild((c) => ({ ...c, historical_exclusive_breastfeeding: TRI[e.target.value] }))}>
                  <option value="yes">Yes</option><option value="no">No</option><option value="unknown">Unknown</option>
                </select>
              </label>
              <label className={label}>Supplement use
                <select className={field} value={triOf(child.supplement_use)} onChange={(e) => setChild((c) => ({ ...c, supplement_use: TRI[e.target.value] }))}>
                  <option value="yes">Yes</option><option value="no">No</option><option value="unknown">Unknown</option>
                </select>
              </label>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Feasibility checks" subtitle="Unknown never passes: it stays unresolved for a professional" />
            <CardBody className="space-y-3">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted">
                  <tr><th className="pb-1 font-medium">Check</th>{Object.values(FEATURES).map((f) => <th key={f} className="pb-1 font-medium">{f.split(' ')[0]} {f.split(' ')[1]}</th>)}</tr>
                </thead>
                <tbody>
                  {Object.entries(CHECKS).map(([k, text]) => (
                    <tr key={k} className="border-t border-line">
                      <td className="py-1.5 pr-2 text-primary">{text}</td>
                      {Object.keys(FEATURES).map((f) => (
                        <td key={f} className="py-1.5">
                          <select aria-label={`${text}: ${FEATURES[f]}`} className="rounded-md border border-line px-1.5 py-1 text-xs" value={triOf(checks[k][f])}
                            onChange={(e) => setChecks((c) => ({ ...c, [k]: { ...c[k], [f]: TRI[e.target.value] } }))}>
                            <option value="yes">yes</option><option value="no">no</option><option value="unknown">unknown</option>
                          </select>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="grid grid-cols-2 gap-3">
                <label className={label}>Budget (units)<input className={field} type="number" min="0" value={budget} onChange={(e) => setBudget(e.target.value)} /></label>
                <label className={label}>Changes per card
                  <select className={field} value={maxChanges} onChange={(e) => setMaxChanges(Number(e.target.value))}><option value={1}>1</option><option value={2}>up to 2</option></select>
                </label>
                <label className={`${label} col-span-2`}>Search method
                  <select className={field} value={method} onChange={(e) => setMethod(e.target.value)}>
                    {Object.entries(METHODS).map(([k, m]) => <option key={k} value={k}>{m.label}</option>)}
                  </select>
                </label>
              </div>
              <Button type="submit" variant="c2" className="w-full" disabled={busy}>
                <Sparkles size={15} /> {busy ? 'Searching…' : 'Find interventions'}
              </Button>
            </CardBody>
          </Card>
        </form>

        <div className="space-y-4">
          {!result ? (
            <Card><CardBody><Empty>Fill in the child and press “Find interventions”.</Empty></CardBody></Card>
          ) : (
            <>
              <Card>
                <CardBody className="flex flex-wrap items-center gap-3">
                  <span className="text-sm text-muted">Current category</span>
                  <Badge tone={result.condition_category === 'higher_concern' ? 'warning' : 'success'}>{result.condition_category.replace('_', ' ')}</Badge>
                  <span className="text-sm text-primary">{result.message}</span>
                  {result.professional_referral_recommended && <Badge tone="danger">{result.referral_message || 'professional referral recommended'}</Badge>}
                </CardBody>
              </Card>
              {result.cards.length === 0 && <Card><CardBody><Empty>No feasible change found under these constraints.</Empty></CardBody></Card>}
              {result.cards.map((card) => (
                <Card key={card.rank} className="overflow-hidden">
                  <div className="flex">
                    <div className="w-1 bg-c2" />
                    <CardBody className="flex-1 space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-c2/10 text-sm font-bold text-c2">{card.rank}</span>
                        <p className="font-semibold text-primary">{card.title || `Option ${card.rank}`}</p>
                        <Badge tone="success">{card.feasibility_status}</Badge>
                        {card.professional_review_required && <Badge tone="info"><UserCheck size={12} /> professional review</Badge>}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {card.changes.map((ch) => (
                          <span key={ch.feature} className="inline-flex items-center gap-2 rounded-lg border border-line bg-slate-50 px-3 py-1.5 text-sm">
                            <span className="text-muted">{FEATURES[ch.feature] || ch.feature}</span>
                            <span className="tabular font-semibold">{String(ch.from_value)}</span>
                            <ArrowRight size={14} className="text-c2" />
                            <span className="tabular font-semibold text-c2">{String(ch.to_value)}</span>
                          </span>
                        ))}
                      </div>
                      <p className="text-sm text-muted">{card.reason || card.explanation}</p>
                      {card.food_options?.length > 0 && <p className="text-sm"><span className="font-medium">Food options: </span>{card.food_options.join(', ')}</p>}
                      {card.incremental_cost_lkr && <p className="text-sm"><span className="font-medium">Extra cost: </span>LKR {card.incremental_cost_lkr} {card.cost_period}</p>}
                    </CardBody>
                  </div>
                </Card>
              ))}
              {result.rejected_or_unresolved?.length > 0 && (
                <Card>
                  <CardHeader title="Not recommended" subtitle="Rejected by a check, or unresolved because a check was unknown" />
                  <CardBody className="space-y-2">
                    {result.rejected_or_unresolved.map((r, i) => (
                      <div key={i} className="flex flex-wrap items-start gap-2 text-sm">
                        <Badge tone={r.status === 'rejected' ? 'danger' : 'neutral'}>{r.status}</Badge>
                        <span className="font-medium">{r.changes.map((c) => `${FEATURES[c.feature] || c.feature} ${c.from_value}→${c.to_value}`).join(' + ')}</span>
                        <span className="text-muted">{r.reasons.join('; ')}</span>
                      </div>
                    ))}
                  </CardBody>
                </Card>
              )}
              <p className="flex items-start gap-2 text-xs text-muted"><Info size={14} className="mt-0.5 shrink-0" /> {result.provenance}. A predicted category change is not a treatment effect.</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
