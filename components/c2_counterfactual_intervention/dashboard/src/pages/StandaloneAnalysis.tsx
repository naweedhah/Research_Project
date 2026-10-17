import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowRight, ChevronLeft, ChevronRight, ExternalLink, Printer, RotateCcw } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { getLocalProfiles, getLocalValidation, getStandaloneAnalysis, getStandaloneValidation } from '../lib/api'
import { localValidationSchema, standaloneResultSchema, type AutomaticCaseId, type LocalValidation, type StandaloneResult, type StandaloneValidation } from '../lib/contracts'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { ErrorState, LoadingState } from '../components/ui/states'

const profiles: { id: AutomaticCaseId; age: number; label: string }[] = [
  { id: 'synthetic_24m', age: 24, label: '24 months' },
  { id: 'synthetic_59m', age: 59, label: '59 months' },
  { id: 'synthetic_5m', age: 5, label: '5 months — safety case' },
]
const featureName: Record<string, string> = { meal_frequency: 'Meal frequency', dietary_diversity: 'Dietary diversity' }
type CardResult = StandaloneResult['cards'][number]

export function StandaloneAnalysis() {
  const navigate = useNavigate()
  const [caseId, setCaseId] = useState<AutomaticCaseId>('synthetic_24m')
  const [budget, setBudget] = useState('1500')
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly'>('weekly')
  const [error, setError] = useState('')
  const [source, setSource] = useState<'demo' | 'local'>(() => new URLSearchParams(window.location.search).get('source') === 'local' ? 'local' : 'demo')
  const [localCaseId, setLocalCaseId] = useState(() => new URLSearchParams(window.location.search).get('case') || '')
  const localProfiles = useQuery({ queryKey: ['local-validation-profiles'], queryFn: getLocalProfiles, retry: false })
  const run = useMutation({ mutationFn: getStandaloneAnalysis })
  const localRun = useMutation({ mutationFn: getLocalValidation })

  function analyze() {
    if (budget.trim() && (!/^\d+(\.\d{1,2})?$/.test(budget.trim()) || Number(budget) > 9999999999)) {
      setError('Enter a nonnegative LKR amount with up to two decimal places, or leave it blank.')
      return
    }
    setError('')
    if (source === 'local') {
      const selected = localCaseId || localProfiles.data?.profiles[0]?.case_id
      if (!selected) { setError('No local validation profile is available.'); return }
      localRun.mutate({ case_id: selected, budget_lkr: budget.trim() || null, budget_period: period }, {
        onSuccess: data => { sessionStorage.setItem('c2-local-validation-result', JSON.stringify(data)); navigate('/analysis/results', { state: data }) },
      })
      return
    }
    run.mutate({ case_id: caseId, budget_lkr: budget.trim() || null, budget_period: period }, {
      onSuccess: data => { sessionStorage.setItem('c2-standalone-result', JSON.stringify(data)); navigate('/analysis/results', { state: data }) },
    })
  }

  return <div className="mx-auto max-w-5xl space-y-7">
    <div className="page-title"><div><span className="eyebrow">Component 2</span><h1>Intervention Analysis</h1><p>Choose a demonstration profile and family budget. Results open on a separate page.</p></div></div>
    <Card className="overflow-hidden p-0"><div className="bg-gradient-to-r from-[#0c3548] via-[#087b89] to-[#17a5a0] p-7 text-white md:p-9"><span className="text-sm font-bold uppercase tracking-widest text-cyan-100">{source === 'local' ? 'Local C1 research validation' : 'Research test mode'}</span><h2 className="mt-3 text-3xl font-bold">Explore feeding changes and food options</h2><p className="mt-3 max-w-2xl text-base text-cyan-50">{source === 'local' ? 'Genuine model comparison on a de-identified local research profile. No intervention approval.' : 'Demonstration data only. Results require professional review.'}</p></div>
      {localProfiles.data && localProfiles.data.profiles.length > 0 && <div className="flex flex-wrap gap-3 border-b border-[var(--line)] p-5 md:px-9"><Button variant={source === 'demo' ? 'default' : 'outline'} onClick={() => setSource('demo')}>Standalone research test</Button><Button variant={source === 'local' ? 'default' : 'outline'} onClick={() => setSource('local')}>Local C1 validation profiles</Button></div>}
      <div className="grid gap-6 p-6 md:grid-cols-3 md:p-9"><label><span className="field-label">{source === 'local' ? 'Source-labelled validation profile' : 'Child age'}</span>{source === 'local' ? <select className="field" aria-label="Source-labelled validation profile" value={localCaseId || localProfiles.data?.profiles[0]?.case_id || ''} onChange={event => setLocalCaseId(event.target.value)}>{localProfiles.data?.profiles.map(profile => <option key={profile.case_id} value={profile.case_id}>{profile.case_id} · {profile.age_months} months · {profile.model_status.replaceAll('_', ' ')}</option>)}</select> : <select className="field" aria-label="Child age" value={caseId} onChange={event => { setCaseId(event.target.value as AutomaticCaseId); run.reset() }}>{profiles.map(profile => <option key={profile.id} value={profile.id}>{profile.label}</option>)}</select>}</label>
          <label><span className="field-label">Food budget · LKR</span><input className="field" aria-label="Food budget LKR" inputMode="decimal" value={budget} onChange={event => { setBudget(event.target.value); run.reset() }} placeholder="Unknown"/></label><label><span className="field-label">Budget period</span><select className="field" aria-label="Budget period" value={period} onChange={event => { setPeriod(event.target.value as typeof period); run.reset() }}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label>
      </div><div className="flex flex-wrap items-center justify-between gap-4 border-t border-[var(--line)] px-6 py-5 md:px-9"><p className="text-base text-[var(--muted)]">{source === 'local' ? 'C1 live re-score · feeding observation provenance unverified' : `Age ${profiles.find(profile => profile.id === caseId)?.age} months · C1 connection not needed`}</p><Button disabled={run.isPending || localRun.isPending} onClick={analyze}>{run.isPending || localRun.isPending ? 'Analyzing…' : source === 'local' ? 'Validate with real C1' : 'Generate intervention plans'} <ArrowRight size={17}/></Button></div>
          {error && <p role="alert" className="mt-2 text-sm text-rose-500">{error}</p>}
    </Card>
    {run.isPending && <LoadingState label="Checking feeding changes and food options…"/>}
    {run.isError && <ErrorState title="Analysis unavailable" detail={run.error.message} retry={analyze}/>}
    {localRun.isPending && <LoadingState label="Rechecking the source-labelled profile with genuine C1…"/>}
    {localRun.isError && <ErrorState title="Local model validation unavailable" detail={localRun.error.message} retry={analyze}/>}
  </div>
}

export function StandaloneResults() {
  const location = useLocation()
  let stored: unknown = location.state
  if (!stored) { try { stored = JSON.parse(sessionStorage.getItem('c2-local-validation-result') || 'null') } catch { stored = null } }
  const localParsed = localValidationSchema.safeParse(stored)
  if (localParsed.success) return <LocalValidationResults result={localParsed.data}/>
  if (!stored) { try { stored = JSON.parse(sessionStorage.getItem('c2-standalone-result') || 'null') } catch { stored = null } }
  const parsed = standaloneResultSchema.safeParse(stored)
  if (!parsed.success) return <Card className="p-8"><h1 className="text-2xl font-bold">No analysis to show</h1><Link className="text-link mt-4 inline-block" to="/analysis">Start an analysis</Link></Card>
  return <Results result={parsed.data}/>
}

function LocalValidationResults({ result }: { result: LocalValidation }) {
  return <div className="space-y-7">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><span className="eyebrow">Local research profile · genuine C1</span><h1 className="mt-2 text-3xl font-bold">Model comparison evidence</h1></div><Link className="text-link text-base" to={`/analysis?source=local&case=${encodeURIComponent(result.case_id)}`}>← Choose another profile or budget</Link></div>
    <div className="rounded-2xl border border-amber-300 bg-amber-50 px-5 py-4 text-base text-amber-950 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100"><strong>Model-only research result.</strong><span className="ml-2">No intervention is authorized. The source does not verify that feeding fields were directly observed; individual suitability and local availability are unknown.</span></div>
    <Card className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4"><Summary label="Local case alias" value={result.case_id}/><Summary label="2025 age" value={`${result.profile.age_months} months`}/><Summary label="Historical height / weight" value={`${result.profile.historical_height_cm} cm / ${result.profile.historical_weight_kg} kg`}/><Summary label="Budget" value={result.budget.amount_lkr ? `LKR ${result.budget.amount_lkr} / ${result.budget.period}` : 'Unknown'}/></Card>
    <Card className="p-5"><div className="flex flex-wrap gap-3"><span className="state-pill">Live {result.model_version}</span><span className="state-pill">Input verified against saved evidence</span><span className="state-pill">allow_demo=false</span></div><h2 className="mt-5 text-xl font-bold">Original model prediction</h2><p className="mt-1 text-base">Meal frequency: {result.profile.original_feeding.meal_frequency} · Dietary diversity: {result.profile.original_feeding.dietary_diversity}</p><RealPrediction prediction={result.baseline}/><p className="mt-3 text-sm text-[var(--muted)]">Source: linked PHM 2025 research workbook · fingerprint {result.input_fingerprint.slice(0, 16)}…</p></Card>
    <section aria-label="Genuine model comparison cards"><h2 className="mb-4 text-2xl font-bold">Model-rule-passing comparisons ({result.cards.length})</h2>{result.cards.length ? <div className="space-y-5">{result.cards.map(card => <LocalModelCard key={card.rank} card={card}/>)}</div> : <Card className="p-6 text-base">No candidate passes the unchanged model rules for this profile. The rejected comparisons below show why.</Card>}</section>
    <details className="panel p-5"><summary className="cursor-pointer text-lg font-semibold">All genuine C1 comparisons ({result.candidates.length})</summary><div className="mt-4 grid gap-4 lg:grid-cols-2">{result.candidates.map((candidate, index) => <div key={index} className="rounded-xl border border-[var(--line)] p-4"><strong>{candidate.model_rule_pass ? 'Model rules passed' : 'Rejected or unresolved'} · Candidate {index + 1}</strong>{Object.entries(candidate.changes).map(([feature, change]) => <p key={feature} className="mt-1 text-base">{featureName[feature] ?? feature}: {change.from} → {change.to}</p>)}<RealPrediction prediction={candidate.prediction}/><p className="mt-3 text-sm">Underweight {pp(candidate.probability_delta.underweight)} · Stunting {pp(candidate.probability_delta.stunting)} · MAM {pp(candidate.probability_delta.MAM)} · SAM {pp(candidate.probability_delta.SAM)}</p><p className="mt-2 text-sm text-[var(--muted)]">{candidate.reasons.length ? candidate.reasons.join('; ') : 'No model-only rule failure. Research authorization and feasibility remain unresolved.'}</p></div>)}</div></details>
    <Card className="p-5"><h2 className="text-lg font-bold">Provenance and limitations</h2><ul className="mt-3 list-inside list-disc space-y-1 text-base">{result.limitations.map(item => <li key={item}>{item}</li>)}</ul><p className="mt-3 break-all text-sm text-[var(--muted)]">Source SHA-256: {result.source_sha256}. This screen re-runs the unchanged trained model and compares its output with locally stored evidence. No private source workbook is bundled with the dashboard.</p></Card>
  </div>
}

function LocalModelCard({ card }: { card: LocalValidation['cards'][number] }) {
  const [planIndex, setPlanIndex] = useState(0)
  const [dayIndex, setDayIndex] = useState(0)
  const plan = card.food_plans[planIndex]
  const day = plan?.schedule[dayIndex]
  return <Card className="overflow-hidden p-0"><div className="bg-gradient-to-r from-indigo-800 via-cyan-800 to-teal-700 p-5 text-white md:p-7"><span className="text-sm font-bold uppercase tracking-wider text-cyan-100">#{card.rank} · passed model comparison only</span><h3 className="mt-2 text-2xl font-bold">Hypothetical feeding change</h3><p className="mt-1 text-base text-cyan-50">Feasibility and research authorization unresolved. Not an intervention prescription.</p></div><div className="space-y-5 p-5 md:p-7"><div className="grid gap-3 md:grid-cols-2">{Object.entries(card.candidate.changes).map(([feature, change]) => <div key={feature} className="rounded-xl bg-[var(--field)] p-4"><span className="text-sm text-[var(--muted)]">{featureName[feature] ?? feature}</span><strong className="mt-1 block text-lg">{change.from} → {change.to}</strong></div>)}</div><div className="rounded-xl border border-[var(--line)] p-4"><strong>Actual C1 comparison</strong><RealPrediction prediction={card.candidate.prediction}/><p className="mt-2 text-sm">Underweight {pp(card.candidate.probability_delta.underweight)} · Stunting {pp(card.candidate.probability_delta.stunting)} · MAM {pp(card.candidate.probability_delta.MAM)} · SAM {pp(card.candidate.probability_delta.SAM)}</p></div>{plan && <div className="rounded-xl border border-[var(--line)] p-4"><div className="flex flex-wrap items-center justify-between gap-3"><h4 className="text-xl font-bold">Illustrative 7-day food option</h4><span className="state-pill">{plan.budget_fit.replaceAll('_', ' ')}</span></div><label className="mt-4 block max-w-lg"><span className="field-label">Compare shopping examples</span><select className="field" aria-label={`Shopping example for model signal ${card.rank}`} value={planIndex} onChange={event => { setPlanIndex(Number(event.target.value)); setDayIndex(0) }}>{card.food_plans.map((option, index) => <option key={option.title} value={index}>#{option.rank} · {option.title}</option>)}</select></label><p className="mt-3 text-base">DCS Colombo reference cost: {plan.estimated_total_lkr === null ? 'Unresolved' : `LKR ${plan.estimated_total_lkr}`} / {plan.cost_period}. Household budget fit is illustrative only.</p>{day && <div className="mt-4 rounded-xl bg-[var(--field)] p-4"><div className="flex items-center justify-between"><strong>{day.day} · day {dayIndex + 1}/7</strong><div className="flex gap-2"><Button variant="outline" aria-label="Previous example day" disabled={dayIndex === 0} onClick={() => setDayIndex(dayIndex - 1)}><ChevronLeft size={16}/></Button><Button variant="outline" aria-label="Next example day" disabled={dayIndex === plan.schedule.length - 1} onClick={() => setDayIndex(dayIndex + 1)}><ChevronRight size={16}/></Button></div></div>{day.slots.map(slot => <p key={slot.label} className="mt-2 text-sm"><strong>{slot.label}:</strong> {slot.foods.map(food => food.name).join(', ')}</p>)}</div>}<p className="mt-3 text-sm text-[var(--muted)]">Household purchase example, not child portions or a treatment plan. Local prices and suitability are unverified.</p></div>}</div></Card>
}

function Results({ result }: { result: StandaloneResult }) {
  return <div className="space-y-7">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><span className="eyebrow">Component 2 results</span><h1 className="mt-2 text-3xl font-bold">Ranked intervention plans</h1></div><Link className="text-link text-base" to="/analysis">← Change profile or budget</Link></div>
    <div className="rounded-2xl border border-amber-300 bg-amber-50 px-5 py-4 text-base text-amber-950 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100"><strong>Research test mode · simulated predictor.</strong><span className="ml-2">Not C1 or clinical advice. Professional review required.</span></div>
    <Card className="grid grid-cols-2 gap-3 p-4 md:grid-cols-4 md:p-5"><Summary label="Profile" value={`${result.profile.age_months} months`}/><Summary label="Budget" value={result.budget.amount_lkr ? `LKR ${result.budget.amount_lkr} / ${result.budget.period}` : 'Unknown'}/><Summary label="Original meal frequency" value={result.original_feeding?.meal_frequency ?? 'Not scored'}/><Summary label="Original dietary diversity" value={result.original_feeding?.dietary_diversity ?? 'Not scored'}/></Card>
    {result.baseline && (result.baseline.severity === 'Severe' || result.baseline.uncertainty_flag) && <Card className="border-amber-400 p-5 text-base font-semibold">Professional assessment is needed for severe or uncertain status.</Card>}
    <section aria-label="Ranked intervention cards"><div className="mb-5 flex items-end justify-between"><h2 className="text-2xl font-bold">Intervention cards</h2><span className="state-pill">{result.cards.length} research-test eligible</span></div>{result.cards.length ? result.cards.map(card => <EligibleCard key={card.rank} card={card} original={result.original_feeding} guidance={result.guidance}/>) : <Card className="p-6 text-base">No eligible research-test candidate. {result.message}</Card>}</section>
    {result.food_plans.length > 0 && <details className="panel p-5"><summary className="cursor-pointer text-lg font-semibold">Compare all educational food options</summary><div className="mt-5 grid gap-3 md:grid-cols-2">{result.food_plans.map(plan => <div key={plan.title} className="rounded-xl border border-[var(--line)] p-4"><strong>#{plan.rank} · {plan.title}</strong><p className="mt-2 text-base">{plan.estimated_total_lkr === null ? 'Cost unresolved' : `LKR ${plan.estimated_total_lkr}`} / {plan.cost_period} · {plan.budget_fit.replaceAll('_',' ')}</p><p className="mt-2 text-sm text-[var(--muted)]">{plan.ranking_reason}</p></div>)}</div></details>}
    {result.rejected_or_unresolved.length > 0 && <details className="panel p-5"><summary className="cursor-pointer text-lg font-semibold">Rejected or unresolved candidates ({result.rejected_or_unresolved.length})</summary><ul className="mt-4 space-y-3">{result.rejected_or_unresolved.map((item, index) => <li key={index} className="rounded-xl border border-[var(--line)] p-4"><strong>{item.method.replaceAll('_',' ')} · {item.status}</strong><p>{Object.entries(item.changes).map(([key, value]) => `${featureName[key] ?? key}: ${value}`).join('; ')}</p><p className="text-[var(--muted)]">{item.reasons.join('; ')}</p></li>)}</ul></details>}
    <RealModelEvidence caseId={result.case_id} fingerprint={result.input_fingerprint}/>
    <details className="panel p-5"><summary className="cursor-pointer text-lg font-semibold">Sources and research limits</summary><p className="mt-4 text-base">Food groups: {result.guidance.note}</p>{result.guidance.reference && <a className="text-link mt-3 inline-flex items-center gap-1" href={result.guidance.reference.url} target="_blank" rel="noreferrer">Sri Lanka Ministry of Health guidance <ExternalLink size={16}/></a>}<p className="mt-3 text-base">Prices are DCS Colombo references. Local prices, availability, suitability and meal portions are unverified. Food options are educational and do not establish treatment effects.</p><p className="mt-3 text-base">Methods: {result.methods.map(method => `${method.name.replaceAll('_',' ')} (${method.eligible_count})`).join(' · ')}. <Link className="text-link" to="/model-validation">Genuine C1 validation</Link> remains separate.</p></details>
  </div>
}

const pct = (value: number) => `${(value * 100).toFixed(2)}%`
const pp = (value: number) => `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)} pp`

function RealModelEvidence({ caseId, fingerprint }: { caseId: AutomaticCaseId; fingerprint: string }) {
  const [open, setOpen] = useState(false)
  const validation = useMutation({ mutationFn: getStandaloneValidation })
  function toggle() { if (!open && !validation.data && !validation.isPending) validation.mutate(caseId); setOpen(!open) }
  return <section className="panel overflow-hidden"><button className="flex w-full items-center justify-between gap-4 p-5 text-left text-lg font-bold" aria-expanded={open} onClick={toggle}><span>Real GA-RGCA Validation Evidence</span><span className="text-base font-semibold text-[var(--accent)]">{open ? 'Hide' : 'Expand'}</span></button>
    {open && <div className="space-y-5 border-t border-[var(--line)] p-5"><p className="text-base">Optional genuine C1 model comparison using the same demonstration profile. This cannot approve the research-test cards above.</p>
      {validation.isPending && <LoadingState label="Checking the genuine C1 model and hypothetical inputs…"/>}
      {validation.isError && <div role="status" className="rounded-xl border border-amber-400 p-4 text-base"><strong>C1 unavailable — standalone plans remain available.</strong><p className="mt-1">{validation.error.message}</p><Button className="mt-3" variant="outline" onClick={() => validation.mutate(caseId)}>Retry C1 validation</Button></div>}
      {validation.data && <RealEvidenceContent data={validation.data} fingerprint={fingerprint}/>}
    </div>}
  </section>
}

function RealEvidenceContent({ data, fingerprint }: { data: StandaloneValidation; fingerprint: string }) {
  if (!data.baseline) return <p className="text-base">No C1 comparison for this age. {data.limitations.join(' ')}</p>
  const sameInput = data.input_fingerprint === fingerprint
  if (!sameInput) return <p role="alert" className="text-base text-rose-600">Input mismatch: C1 results are hidden. Run the standalone analysis again.</p>
  return <div className="space-y-5"><div className="flex flex-wrap gap-3"><span className="state-pill">C1 connected · {data.model_version}</span><span className="state-pill">{data.prediction_source}</span><span className="state-pill">Same full input: {sameInput ? 'verified' : 'mismatch'}</span></div>
    <div className="rounded-xl bg-[var(--field)] p-4"><h3 className="text-lg font-bold">Original C1 prediction</h3><RealPrediction prediction={data.baseline}/></div>
    <div className="grid gap-4 xl:grid-cols-3">{data.candidates.map((item, index) => <article key={index} className="rounded-xl border border-[var(--line)] p-4"><div className="flex items-center justify-between gap-2"><h3 className="text-lg font-bold">Candidate {index + 1}</h3><span className={item.model_policy_result === 'rejected' ? 'font-bold text-rose-600' : 'font-bold text-amber-600'}>{item.model_policy_result}</span></div><div className="mt-3 space-y-1">{Object.entries(item.changes).map(([key, change]) => <p key={key} className="text-base"><strong>{featureName[key] ?? key}:</strong> {change.from} → {change.to}</p>)}</div><RealPrediction prediction={item.prediction}/><div className="mt-4 rounded-lg bg-[var(--field)] p-3 text-sm"><strong>Change from original</strong><p>Underweight {pp(item.probability_delta.underweight)} · Stunting {pp(item.probability_delta.stunting)}</p><p>Normal {pp(item.probability_delta.acute.Normal)} · MAM {pp(item.probability_delta.acute.MAM)} · SAM {pp(item.probability_delta.acute.SAM)}</p></div><p className="mt-3 text-sm font-semibold">Model rules: {item.model_policy_result}</p><ul className="mt-1 list-inside list-disc text-sm text-[var(--muted)]">{item.rejected_reasons.map(reason => <li key={reason}>{reason}</li>)}{item.unresolved_reasons.map(reason => <li key={reason}>{reason}</li>)}</ul><p className="mt-3 text-sm text-[var(--muted)]">Only permitted feeding fields changed: {item.only_feeding_fields_changed ? 'verified' : 'not verified'}</p></article>)}</div>
    <div className="rounded-xl border border-[var(--line)] p-4"><strong>Provenance and limits</strong><p className="mt-2 text-base">GA-RGCA-v3 on invented C2 inputs with allow_demo=false. {data.limitations.join(' ')}</p></div>
  </div>
}

function RealPrediction({ prediction }: { prediction: NonNullable<StandaloneValidation['baseline']> }) {
  return <div className="mt-3 text-sm"><p className="font-semibold">{prediction.predicted_malnutrition_type} · {prediction.severity} · uncertainty {prediction.uncertainty_flag ? 'flagged' : 'not flagged'}</p><p className="mt-2">Underweight {pct(prediction.underweight_probability)} · Stunting {pct(prediction.stunting_probability)}</p><p>Normal {pct(prediction.acute_probabilities.Normal)} · MAM {pct(prediction.acute_probabilities.MAM)} · SAM {pct(prediction.acute_probabilities.SAM)}</p></div>
}

function Summary({ label, value }: { label: string; value: string }) { return <div className="min-w-0 rounded-xl border border-[var(--line)] p-3 md:p-4"><span className="block text-sm text-[var(--muted)]">{label}</span><strong className="mt-2 block break-words text-base md:text-lg">{value}</strong></div> }

function EligibleCard({ card, original, guidance }: { card: CardResult; original: StandaloneResult['original_feeding']; guidance: StandaloneResult['guidance'] }) {
  const [planIndex, setPlanIndex] = useState(0)
  const [open, setOpen] = useState(false)
  const [dayIndex, setDayIndex] = useState(0)
  const [completed, setCompleted] = useState<number[]>([])
  const plan = card.food_plans[planIndex]
  const day = plan?.schedule[dayIndex]
  function choosePlan(index: number) { setPlanIndex(index); setDayIndex(0); setCompleted([]); setOpen(false) }
  const colors = ['from-cyan-700 to-teal-600', 'from-indigo-700 to-sky-600', 'from-emerald-700 to-cyan-600']
  return <Card className="mb-6 overflow-hidden p-0"><div className={`bg-gradient-to-r ${colors[(card.rank - 1) % colors.length]} p-6 text-white md:p-7`}><div className="flex flex-wrap items-center justify-between gap-3"><span className="rounded-full bg-white/20 px-4 py-2 text-base font-bold">Rank #{card.rank}</span><span className="rounded-full bg-white px-4 py-2 text-sm font-bold text-slate-800">{card.status}</span></div><h3 className="mt-5 text-2xl font-bold">{Object.keys(card.changes).length === 2 ? 'Meal frequency + dietary diversity' : featureName[Object.keys(card.changes)[0]]}</h3><div className="mt-4 grid gap-3 md:grid-cols-2">{Object.entries(card.changes).map(([key, value]) => <div key={key} className="rounded-xl bg-white/15 p-4"><span className="text-sm font-semibold text-white/85">{featureName[key]}</span><p className="mt-2 text-lg font-bold">{original?.[key] ?? 'unknown'} <span aria-hidden="true">→</span> {value}</p></div>)}</div><p className="mt-4 text-base text-white/90">Supported by {card.supporting_methods.map(method => method.replaceAll('_',' ')).join(', ')} · fewer feeding changes rank first.</p></div>
    <div className="space-y-5 p-6 md:p-7"><div className="flex flex-wrap items-center justify-between gap-3"><div><span className="eyebrow">Educational food option</span><h4 className="mt-1 text-xl font-bold">{plan?.title ?? 'No priced option available'}</h4></div>{plan && <span className="rounded-full bg-teal-100 px-4 py-2 text-sm font-bold text-teal-900 dark:bg-teal-900 dark:text-teal-100">{plan.budget_fit.replaceAll('_',' ')}</span>}</div>
      {plan && <><div className="grid gap-3 sm:grid-cols-3"><Summary label={`Reference cost / ${plan.cost_period}`} value={plan.estimated_total_lkr === null ? 'Unknown' : `LKR ${plan.estimated_total_lkr}`}/><Summary label="Budget remaining" value={plan.budget_remaining_lkr === null ? '—' : `LKR ${plan.budget_remaining_lkr}`}/><Summary label="Shortfall" value={plan.shortfall_lkr === null ? '—' : `LKR ${plan.shortfall_lkr}`}/></div>
      <div className="flex flex-wrap gap-2">{plan.food_groups.map(group => <span key={group} className="rounded-full bg-cyan-100 px-3 py-1.5 text-sm font-semibold text-cyan-950 dark:bg-cyan-900 dark:text-cyan-100">{group}</span>)}</div>
      {card.food_plans.length > 1 && <label className="block max-w-lg"><span className="field-label">Compare educational food options</span><select className="field" aria-label={`Food option for rank ${card.rank}`} value={planIndex} onChange={event => choosePlan(Number(event.target.value))}>{card.food_plans.map((option, index) => <option key={option.title} value={index}>#{option.rank} {option.title} · {option.budget_fit.replaceAll('_',' ')}</option>)}</select></label>}
      <details className="rounded-xl border border-[var(--line)] p-4"><summary className="cursor-pointer text-base font-semibold">Shopping list and price sources</summary><div className="mt-4 grid gap-3 md:grid-cols-2">{plan.items.map(item => <div key={item.food_id} className="rounded-xl bg-[var(--field)] p-4"><strong className="text-base">{item.name}</strong><p className="mt-1 text-base">{item.quantity} {item.unit} · LKR {item.indicative_cost_lkr}</p><a className="text-link mt-2 inline-flex items-center gap-1 text-sm" href={item.source_url} target="_blank" rel="noreferrer">DCS Colombo · {item.observation_end} <ExternalLink size={14}/></a></div>)}</div><p className="mt-4 text-sm text-[var(--muted)]">Illustrative household purchase quantities, not child servings. Colombo reference prices; local availability is unknown.</p></details>
      {plan.schedule.length > 0 ? <div className="border-t border-[var(--line)] pt-5"><div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => setOpen(!open)}>{open ? 'Hide 7-Day Plan' : 'View 7-Day Plan'}</Button><Button variant="ghost" onClick={() => { setOpen(true); requestAnimationFrame(() => window.print()) }}><Printer size={16}/> Print Plan</Button></div>{open && day && <div className="meal-schedule mt-4 rounded-xl border border-[var(--line)] p-5"><div className="flex items-center justify-between"><div><span className="eyebrow">Day {dayIndex + 1} of 7</span><h5 className="text-xl font-bold">{day.day}</h5></div><span className="state-pill">{completed.length}/7 demo days</span></div><div className="mt-4 grid gap-3 md:grid-cols-3">{day.slots.map(slot => <div key={slot.label} className="rounded-xl bg-[var(--field)] p-4"><strong>{slot.label}</strong><ul className="mt-2 space-y-2">{slot.foods.map(food => <li key={food.name}>{food.name} <span className="text-sm text-[var(--muted)]">· {food.food_group}</span></li>)}</ul></div>)}</div><div className="mt-5 flex flex-wrap gap-2"><Button variant="outline" disabled={dayIndex === 0} onClick={() => setDayIndex(dayIndex - 1)}><ChevronLeft size={16}/> Previous day</Button><Button variant="outline" disabled={dayIndex === 6} onClick={() => setDayIndex(dayIndex + 1)}>Continue Plan <ChevronRight size={16}/></Button><Button variant="ghost" onClick={() => setCompleted(completed.includes(dayIndex) ? completed.filter(index => index !== dayIndex) : [...completed, dayIndex])}>{completed.includes(dayIndex) ? 'Unmark day' : 'Mark demo day completed'}</Button><Button variant="ghost" onClick={() => { setDayIndex(0); setCompleted([]) }}><RotateCcw size={16}/> Reset schedule</Button></div></div>}</div> : <p className="text-base">Schedule unavailable: price or food-group evidence is incomplete.</p>}
      <p className="text-base font-medium text-[var(--muted)]">Food examples are separate from candidate acceptance. They do not prove dietary adequacy or treatment benefit. Individual suitability and availability need review.</p>{guidance.reference && <a className="text-link inline-flex items-center gap-1" href={guidance.reference.url} target="_blank" rel="noreferrer">Food-group guidance <ExternalLink size={16}/></a>}</>}
    </div>
  </Card>
}
